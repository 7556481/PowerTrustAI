"""Opt-in private model data. Never archive transport, credentials or settings."""
import hashlib
import json
from pathlib import Path
from uuid import uuid4
from core.validation import InputError


LOCAL_ROOT = Path(__file__).resolve().parents[1] / "data" / "retrieval_local"


class DiagnosticStorageError(RuntimeError):
    code = "DIAGNOSTIC_STORAGE_FAILED"
    def __init__(self):
        super().__init__("Private response diagnostic could not be saved")


class ResponseDiagnostics:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        if not self.directory.is_relative_to(LOCAL_ROOT.resolve()):
            raise InputError("Response diagnostics must be inside ignored data/retrieval_local")

    def save(self, response, record, diagnostic, *, request_messages_path=None):
        # This allowlist deliberately excludes messages, credentials and transport.
        payload = {"scope": "PRIVATE_MODEL_RESPONSE_DIAGNOSTIC", "schema_version": 1,
                   "call_number": record.call_number, "prompt_version": record.prompt_version,
                   "response_contract_version": record.response_contract_version,
                   "candidate_catalog_path": record.candidate_catalog_path,
                   "input_snapshot_path": record.input_snapshot_path,
                   "request_metrics": record.request_metrics,
                   "correction": record.correction, "model_id": response.model_id,
                   "finish_reason": response.finish_reason, "response_text": response.text,
                   "response_sha256": hashlib.sha256(response.text.encode("utf-8")).hexdigest(),
                   "validation_error": diagnostic}
        if request_messages_path is not None:
            payload['request_messages_path']=request_messages_path
        try:
            if not self.directory.resolve().is_relative_to(LOCAL_ROOT.resolve()):
                raise OSError()
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / f"response-{uuid4().hex}.json"
            with path.open("x", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            return str(path)
        except OSError:
            raise DiagnosticStorageError() from None

    def save_candidates(self, payload):
        """Explicit program catalog allowlist, before API call, preserved on failure."""
        from dataclasses import asdict
        selected = {key:payload[key] for key in ("answer_id","answer_version","knowledge_version",
            "candidate_version","independent_allowed_quote_ids","original_citation_allowed_quote_ids")}
        selected["scope"] = "PRIVATE_PROGRAM_QUOTE_CATALOG"
        selected["candidates"] = [asdict(c) for c in payload["candidates"]]
        try:
            if not self.directory.resolve().is_relative_to(LOCAL_ROOT.resolve()): raise OSError()
            self.directory.mkdir(parents=True,exist_ok=True)
            path = self.directory / f"candidates-{uuid4().hex}.json"
            with path.open("x",encoding="utf-8") as handle:json.dump(selected,handle,ensure_ascii=False,indent=2)
            return str(path)
        except OSError:
            raise DiagnosticStorageError() from None

    def save_scope(self,payload):
        """Only current scoped program candidate data; no credentials/headers."""
        import hashlib
        try:
            if not self.directory.resolve().is_relative_to(LOCAL_ROOT.resolve()):raise OSError()
            self.directory.mkdir(parents=True,exist_ok=True)
            path=self.directory/f"scope-{uuid4().hex}.json"
            digest=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            with path.open("x",encoding="utf-8") as h:json.dump(dict(payload,scope_sha256=digest),h,ensure_ascii=False,indent=2)
            return str(path)
        except OSError:raise DiagnosticStorageError() from None

    def save_messages(self,messages,prompt_version,correction):
        """Explicit role/content only, including correction; before paid request."""
        selected={'scope':'PRIVATE_MODEL_MESSAGES_BEFORE_REQUEST','prompt_version':prompt_version,
            'correction':correction,'messages':[{'role':m.role,'content':m.content} for m in messages]}
        return self.save_scope(selected)

    def save_generation_input(self,inputs,prompt_version,*,answer_id=None,answer_version=1):
        """Before request, explicit input-only allowlist, no settings/auth/headers."""
        from dataclasses import asdict
        data={"scope":"PRIVATE_FULL_GENERATION_INPUT_BEFORE_REQUEST","requested_answer_id":answer_id or inputs.request.task_id+"-answer",
            "requested_answer_version":answer_version,"question":inputs.request.question,"user_context":inputs.request.user_context,
            "engineering_context":None if inputs.request.engineering_context is None else asdict(inputs.request.engineering_context),
            "answer_requirements":inputs.answer_requirements,"prompt_version":prompt_version,"knowledge_version":inputs.knowledge_version,
            "evidence":[asdict(e) for e in inputs.evidence],"evidence_bindings":[asdict(b) for b in inputs.evidence_bindings]}
        digest=hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode("utf-8")).hexdigest()
        try:
            if not self.directory.resolve().is_relative_to(LOCAL_ROOT.resolve()):raise OSError()
            self.directory.mkdir(parents=True,exist_ok=True)
            path=self.directory/f"generation-input-{uuid4().hex}.json"
            with path.open("x",encoding="utf-8") as h:json.dump(dict(data,input_sha256=digest),h,ensure_ascii=False,indent=2)
            return str(path)
        except OSError:raise DiagnosticStorageError() from None
