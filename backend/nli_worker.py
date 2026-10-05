"""Isolated read-only CPU inference worker; never loads .env or calls an API."""
import argparse,json,time,hashlib,sys,os,threading
from pathlib import Path
from evaluation.support_nli import load_model,VERSION

def decode_request(line):
 return json.loads(line.decode('utf-8'))

def main():
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--profile',required=True);a=p.parse_args()
 try:
  import psutil
  ownership=decode_request(sys.stdin.buffer.readline())
  owners=[(psutil.Process(ownership[k]),psutil.Process(ownership[k]).create_time()) for k in ('owner_pid','launcher_pid')]
  def owner_watch():
   while True:
    time.sleep(.1)
    try:
     if any(not process.is_running() or process.create_time()!=created for process,created in owners):os._exit(0)
    except psutil.Error:os._exit(0)
  threading.Thread(target=owner_watch,daemon=True).start()
  directory=Path(a.checkpoint);profile=json.loads(Path(a.profile).read_text(encoding='utf-8'))
  if profile['epoch']!=1 or profile['adapter_version']!=VERSION or profile['base_model']!='cross-encoder/nli-MiniLM2-L6-H768' or profile['base_revision']!='b95119ce93d3e065de6214e38cd4a97b0f2f2c6d':raise ValueError('Profile mismatch')
  if profile['weight_sha256']!='c49122c7c07ae56c7381d014ddffa46dfae373cf63265657284a51fbcf24a358' or profile['checkpoint_files'].get('model.safetensors',{}).get('sha256')!=profile['weight_sha256'] or 'config.json' not in profile['checkpoint_files']:raise ValueError('Fixed epoch1 weights required')
  for name,record in profile['checkpoint_files'].items():
   if Path(name).name!=name or hashlib.sha256((directory/name).read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Checkpoint changed')
  import torch
  torch.set_num_threads(4);model,tokenizer,mapping,limit,seconds,info=load_model(directory);model.eval()
  identity={k:profile[k] for k in ('version','base_model','base_revision','epoch','adapter_version','weight_sha256','selection_seal_sha256')}
  identity.update(mapping=mapping,context_limit=limit,load_seconds=seconds,loading_info=info,device='cpu',rss_bytes=psutil.Process().memory_info().rss,worker_pid=os.getpid())
  print(json.dumps({'ready':True,'identity':identity}),flush=True)
 except Exception:
  print(json.dumps({'ready':False,'code':'MODEL_UNAVAILABLE'}),flush=True);return
 for line in sys.stdin.buffer:
  try:
   pair=decode_request(line)['pair'];started=time.perf_counter()
   tensors=tokenizer(pair['premise'],pair['hypothesis'],truncation=False,return_tensors='pt');length=tensors['input_ids'].shape[1]
   if length>limit:result={'status':'skipped','reason':'over_context_no_truncation','tokens':length,'context_limit':limit}
   else:
    with torch.inference_mode():logits=model(**tensors).logits[0]
    if not torch.isfinite(logits).all():raise ValueError('Nonfinite logits')
    result={'status':'complete','reason':None,'tokens':length,'context_limit':limit,'nli_three_class_result':mapping[int(logits.argmax())],
        'logits':logits.tolist(),'logits_label_order':[mapping[i] for i in range(3)],'scores_are_calibrated':False,
        'seconds':time.perf_counter()-started,'rss_bytes':psutil.Process().memory_info().rss}
   print(json.dumps(result),flush=True)
  except Exception as exc:print(json.dumps({'status':'failed','reason':'local_inference_error','error_type':type(exc).__name__}),flush=True)

if __name__=='__main__':main()
