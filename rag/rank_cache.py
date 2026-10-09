"""Per-run bounded numeric ranking work only; no Evidence or model judgments."""
from collections import OrderedDict
from types import MappingProxyType
from threading import Lock

class RankCache:
    def __init__(self,limit=8,max_results=64):
        self.limit=limit;self.max_results=max_results;self.entries=OrderedDict();self.lock=Lock()
    def get(self,key):
        with self.lock:
            value=self.entries.get(key)
            if value is not None:self.entries.move_to_end(key)
            return value
    def put(self,key,rows):
        if key[-1]>self.max_results or len(key[-2])>4096:return
        with self.lock:
            self.entries[key]=tuple(MappingProxyType({'rowid':r['rowid'],'score':r['score']}) for r in rows)
            self.entries.move_to_end(key)
            while len(self.entries)>self.limit:self.entries.popitem(last=False)
    def clear(self):
        with self.lock:self.entries.clear()
