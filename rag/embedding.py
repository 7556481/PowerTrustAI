"""Local, pinned E5 ONNX encoder. Optional imports never reach offline Harness."""
import hashlib
import json
from pathlib import Path
import urllib.request

from core.validation import ContractError, InputError

MODEL_ID = "intfloat/multilingual-e5-small"
REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
ARTIFACTS = {
    "onnx/model.onnx": (470268510, "ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665"),
    "tokenizer.json": (17082730, "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39"),
}


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download_model(directory):
    """Public fixed revision only; atomic downloads with independently pinned hashes."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, (size, sha) in ARTIFACTS.items():
        path = directory / name
        if path.exists() and path.stat().st_size == size and file_hash(path) == sha:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".partial")
        try:
            url = f"https://huggingface.co/{MODEL_ID}/resolve/{REVISION}/{name}"
            with urllib.request.urlopen(url, timeout=120) as response, open(temporary, "wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            if temporary.stat().st_size != size or file_hash(temporary) != sha:
                raise ContractError("Model artifact size/SHA-256 mismatch: " + name)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    # Retain upstream license statement and full card, not model-generated metadata.
    card = directory / "README.upstream.md"
    if not card.exists():
        with urllib.request.urlopen(f"https://huggingface.co/{MODEL_ID}/raw/{REVISION}/README.md", timeout=60) as response:
            card.write_bytes(response.read())
    manifest = {"model_id": MODEL_ID, "revision": REVISION, "license": "MIT (upstream model card)",
                "artifacts": {name: {"bytes": size, "sha256": sha} for name, (size, sha) in ARTIFACTS.items()}}
    (directory / "model-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


class E5ONNXEncoder:
    def close(self):
        self.session=None;self.tokenizer=None
    def __init__(self, directory, *, threads=4):
        # No network or automatic dependency installation on construction.
        import numpy as np
        import onnxruntime as ort
        import tokenizers
        directory = Path(directory)
        for name, (size, sha) in ARTIFACTS.items():
            path = directory / name
            if not path.exists() or path.stat().st_size != size or file_hash(path) != sha:
                raise ContractError("Missing/mismatched pinned model artifact: " + name)
        self.np = np
        self.tokenizer = tokenizers.Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        if [self.tokenizer.token_to_id(x) for x in ("<s>", "</s>", "<pad>")] != [0, 2, 1]:
            raise ContractError("Unexpected XLM-R special token mapping")
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(directory / "onnx/model.onnx"), options, providers=["CPUExecutionProvider"])
        self.inputs = {x.name for x in self.session.get_inputs()}
        if not self.inputs <= {"input_ids", "attention_mask", "token_type_ids"}:
            raise ContractError("Unexpected ONNX input contract")
        self.profile = {"model_id": MODEL_ID, "revision": REVISION, "artifact_sha256": ARTIFACTS["onnx/model.onnx"][1],
            "tokenizer_sha256": ARTIFACTS["tokenizer.json"][1], "dimension": 384, "precision": "FP32",
            "normalization": "L2", "metric": "cosine-dot", "pooling": "attention-mask-mean",
            "encoding": "e5-query-passage-v1", "representation": "stored-search-text-v1",
            "long_document": "480-token-windows-stride448-equal-mean-L2-v1", "query_limit": 512,
            "onnxruntime": ort.__version__, "tokenizers": tokenizers.__version__, "numpy": np.__version__,
            "provider": "CPUExecutionProvider", "max_batch": 4}
        self.profile["intra_op_threads"] = threads

    def encode(self, texts, kind):
        if kind not in ("query", "passage"):
            raise InputError("Encoder kind must be query or passage")
        np = self.np
        owners, windows = [], []
        for owner, text in enumerate(texts):
            for window in self.token_windows(text, kind):
                windows.append(window)
                owners.append(owner)
        collected = [[] for _ in texts]
        for start in range(0, len(windows), 4):
            batch = windows[start:start + 4]
            width = max(map(len, batch))
            ids = np.full((len(batch), width), 1, dtype=np.int64)
            mask = np.zeros_like(ids)
            for i, tokens in enumerate(batch):
                ids[i, :len(tokens)] = tokens
                mask[i, :len(tokens)] = 1
            values = {"input_ids": ids, "attention_mask": mask, "token_type_ids": np.zeros_like(ids)}
            hidden = self.session.run(None, {name: values[name] for name in self.inputs})[0]
            if hidden.shape != (len(batch), width, 384):
                raise ContractError("Unexpected ONNX output dimensions")
            pooled = (hidden * mask[..., None]).sum(axis=1) / mask.sum(axis=1)[:, None]
            for owner, vector in zip(owners[start:start + 4], pooled):
                collected[owner].append(vector)
        result = []
        for vectors in collected:
            vector = np.mean(vectors, axis=0)
            norm = np.linalg.norm(vector)
            if not np.isfinite(vector).all() or norm <= 0:
                raise ContractError("Invalid encoder vector")
            result.append(tuple(float(x) for x in vector / norm))
        return result

    def token_windows(self, text, kind):
        """Deterministic representation only; never changes source/Evidence text."""
        if kind not in ("query", "passage"):
            raise InputError("Encoder kind must be query or passage")
        prefix = self.tokenizer.encode(kind + ":", add_special_tokens=False).ids
        windows = []
        if not text.strip():
            raise InputError("Cannot embed blank text")
        full = self.tokenizer.encode(kind + ": " + text, add_special_tokens=False).ids
        if full[:len(prefix)] != prefix:
            raise ContractError("Tokenizer prefix boundary mismatch")
        ids = full[len(prefix):]
        if kind == "query" and len(ids) + len(prefix) + 2 > 512:
            raise InputError("Query exceeds 512 tokens; no silent truncation")
        starts = [0] if kind == "query" else range(0, len(ids), 448)
        for start in starts:
            content = ids if kind == "query" else ids[start:start + 480]
            windows.append([0] + prefix + content + [2])
            if start + 480 >= len(ids):
                break
        return windows
