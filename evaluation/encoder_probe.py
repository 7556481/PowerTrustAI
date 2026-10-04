"""Independent pooling and padding probe, no retrieval or paid API."""
import json
import time
from evaluation.body_priority_trial import BASE
from rag.embedding import E5ONNXEncoder

def main():
    start=time.perf_counter();e=E5ONNXEncoder(BASE/'e5-small');np=e.np
    texts=['voltage stability','正常电压是否证明电压稳定？']
    windows=[e.token_windows(t,'query')[0] for t in texts];width=max(map(len,windows))
    ids=np.full((2,width),1,dtype=np.int64);mask=np.zeros_like(ids)
    for i,w in enumerate(windows):ids[i,:len(w)]=w;mask[i,:len(w)]=1
    hidden=e.session.run(None,{'input_ids':ids,'attention_mask':mask,'token_type_ids':np.zeros_like(ids)})[0]
    manual=[]
    for i,w in enumerate(windows):
        pooled=np.mean(hidden[i,:len(w)].astype(np.float64),axis=0)
        manual.append(pooled/np.linalg.norm(pooled))
    actual=e.encode(texts,'query');single=[e.encode([t],'query')[0] for t in texts]
    result={'manual_pooling_max_abs_error':float(np.max(np.abs(np.asarray(actual)-manual))),
        'padding_batch_vs_single_max_abs_error':float(np.max(np.abs(np.asarray(actual)-single))),
        'output_shape':list(hidden.shape),'seconds':time.perf_counter()-start,'paid_api_calls':0}
    # Windows process peak resident memory, measured within this probe (not the earlier experiment).
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in
            ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    handle=ctypes.windll.kernel32.GetCurrentProcess
    handle.restype=wintypes.HANDLE
    get=ctypes.windll.psapi.GetProcessMemoryInfo
    get.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    if get(handle(),ctypes.byref(counters),counters.cb):result['probe_peak_working_set_bytes']=counters.PeakWorkingSetSize
    with (BASE/'body-priority-v1/encoder-probe.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
