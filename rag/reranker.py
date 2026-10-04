"""Optional local cross-encoder. Relevance logits never imply factual support."""
import hashlib
import json
from pathlib import Path
import time
import urllib.request

MODEL_ID='cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'
REVISION='1427fd652930e4ba29e8149678df786c240d8825'
ARTIFACTS={
    'onnx/model_quint8_avx2.onnx':(118620016,'6c2513767fb63d008a4377bef7a7a3555433d9436342bb53e35a3a72ffc52d4b'),
    'tokenizer.json':(17082660,'62c24cdc13d4c9952d63718d6c9fa4c287974249e16b7ade6d5a85e7bbb75626')}
CONFIG={'version':'mmarco-int8-raw-pair-v1','max_length':512,'truncation':'only_second-right',
    'input':'original query + Evidence.text; no prefixes, extra titles, contexts or labels',
    'batch_size':2,'threads':4,'provider':'CPUExecutionProvider','score':'raw single relevance logit (Identity)'}

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def download(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    for name,(size,sha) in ARTIFACTS.items():
        target=directory/name
        if target.exists() and target.stat().st_size==size and file_hash(target)==sha:continue
        target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix('.partial')
        with urllib.request.urlopen(f'https://huggingface.co/{MODEL_ID}/resolve/{REVISION}/{name}',timeout=120) as r,temp.open('wb') as f:
            while chunk:=r.read(1048576):f.write(chunk)
        if temp.stat().st_size!=size or file_hash(temp)!=sha:raise ValueError('Pinned artifact hash/size mismatch: '+name)
        temp.replace(target)
    for name in ('README.md','config.json','tokenizer_config.json'):
        target=directory/name
        if not target.exists():
            with urllib.request.urlopen(f'https://huggingface.co/{MODEL_ID}/raw/{REVISION}/{name}',timeout=60) as r:
                target.write_bytes(r.read())
    manifest={'model_id':MODEL_ID,'revision':REVISION,'license':'Apache-2.0','downloaded_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'files':{name:{'bytes':(directory/name).stat().st_size,'sha256':file_hash(directory/name)} for name in list(ARTIFACTS)+['README.md','config.json','tokenizer_config.json']}}
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

def pair_encoding(tokenizer,query,text):
    tokenizer.no_padding();tokenizer.no_truncation()
    full=tokenizer.encode(query,text)
    query_tokens=sum(s==0 for s in full.sequence_ids)
    if query_tokens+4>=CONFIG['max_length']:raise ValueError('Query too long: refusing query truncation')
    tokenizer.enable_truncation(max_length=CONFIG['max_length'],strategy='only_second',direction='right')
    encoded=tokenizer.encode(query,text);tokenizer.no_truncation()
    ends=[end for (start,end),s in zip(encoded.offsets,encoded.sequence_ids) if s==1]
    body_tokens=sum(s==1 for s in full.sequence_ids);kept=sum(s==1 for s in encoded.sequence_ids)
    note={'full_pair_tokens':len(full.ids),'encoded_tokens':len(encoded.ids),'query_tokens':query_tokens,
        'body_tokens':body_tokens,'kept_body_tokens':kept,'truncated':kept<body_tokens,
        'kept_body_char_end':max(ends,default=0),'body_chars':len(text),'policy':CONFIG['truncation']}
    return encoded,note

def stable_order(scores, ids):
    import math
    if len(scores)!=len(ids) or len(set(ids))!=len(ids):raise ValueError('Unique candidate IDs and score cardinality required')
    if not all(math.isfinite(s) for s in scores):raise ValueError('Nonfinite relevance logit')
    return sorted(range(len(ids)),key=lambda i:(-scores[i],ids[i]))

class ONNXReranker:
    def __init__(self,directory):
        directory=Path(directory);start=time.perf_counter()
        for name,(size,sha) in ARTIFACTS.items():
            p=directory/name
            if not p.is_file():raise FileNotFoundError('Optional reranker unavailable: '+str(p))
            if p.stat().st_size!=size or file_hash(p)!=sha:raise ValueError('Reranker integrity error: '+name)
        import numpy as np
        import onnxruntime as ort
        import tokenizers
        self.np=np;self.tokenizer=tokenizers.Tokenizer.from_file(str(directory/'tokenizer.json'))
        options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(directory/'onnx/model_quint8_avx2.onnx'),options,providers=['CPUExecutionProvider'])
        self.inputs={x.name for x in self.session.get_inputs()}
        if not self.inputs <= {'input_ids','attention_mask','token_type_ids'}:raise ValueError('Unexpected ONNX inputs')
        self.profile={'model_id':MODEL_ID,'revision':REVISION,'config':CONFIG,'artifacts':ARTIFACTS,
            'onnxruntime':ort.__version__,'tokenizers':tokenizers.__version__,'numpy':np.__version__,
            'inputs':[{ 'name':x.name,'shape':x.shape,'type':x.type} for x in self.session.get_inputs()],
            'outputs':[{ 'name':x.name,'shape':x.shape,'type':x.type} for x in self.session.get_outputs()]}
        self.load_seconds=time.perf_counter()-start
    def score(self,query,texts):
        if not texts:return [],[]
        if not query.strip():raise ValueError('Nonblank query required')
        encodings=[];notes=[]
        for text in texts:
            enc,note=pair_encoding(self.tokenizer,query,text);encodings.append(enc);notes.append(note)
        scores=[];np=self.np
        for start in range(0,len(texts),2):
            batch=encodings[start:start+2];width=max(len(e.ids) for e in batch)
            ids=np.full((len(batch),width),1,dtype=np.int64);mask=np.zeros_like(ids);types=np.zeros_like(ids)
            for i,e in enumerate(batch):
                ids[i,:len(e.ids)]=e.ids;mask[i,:len(e.ids)]=e.attention_mask;types[i,:len(e.ids)]=e.type_ids
            values={'input_ids':ids,'attention_mask':mask,'token_type_ids':types}
            logits=self.session.run(None,{name:values[name] for name in self.inputs})[0]
            if logits.shape!=(len(batch),1):raise ValueError('Expected single relevance logit per pair')
            scores.extend(float(s) for s in logits[:,0])
        return scores,notes

def peak_working_set():
    """Windows process lifetime peak resident memory, including Python/model."""
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in
            ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    c=Counters();c.cb=ctypes.sizeof(c);gethandle=ctypes.windll.kernel32.GetCurrentProcess;gethandle.restype=wintypes.HANDLE
    get=ctypes.windll.psapi.GetProcessMemoryInfo;get.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    if not get(gethandle(),ctypes.byref(c),c.cb):raise OSError('Cannot measure process peak working set')
    return c.PeakWorkingSetSize
