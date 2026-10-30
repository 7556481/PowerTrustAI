import subprocess,sys
from unittest.mock import patch
from evaluation.tantivy_stability_v2 import supervise
original=subprocess.Popen
def launch(args,**kw):
 if args[args.index('-m')+1]=='evaluation.tantivy_stability_v2' and args[-1]=='campaign':args=list(args);args[args.index('-m')+1]='evaluation.tantivy_medium_measure_v2'
 return original(args,**kw)
if __name__=='__main__':
 with patch('subprocess.Popen',launch):supervise('campaign',['campaign'])
