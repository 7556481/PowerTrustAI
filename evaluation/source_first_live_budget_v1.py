"""Per-request durable accounting. No tokenizer claim and no production sender."""
import json,threading
from pathlib import Path

class BudgetStop(RuntimeError):pass

class Ledger:
    def __init__(self,path,*,limit=1200000,calls=96,chain_calls=12):
        self.path=Path(path)
        self.path.mkdir(parents=True,exist_ok=False) # Never recover/replay an attempt.
        self.limit=limit;self.call_limit=calls;self.chain_limit=chain_calls
        self.lock=threading.Lock();self.entries={};self.chains={};self.charged=0;self.stopped=False
    def persist(self,event):
        index=len(list(self.path.glob('*.json')))
        with (self.path/f'{index:04d}.json').open('x',encoding='utf-8') as f:
            json.dump(event,f,ensure_ascii=False);f.flush()
            import os
            os.fsync(f.fileno())
    def stop(self,reason):
        self.stopped=True
        self.persist(dict(event='stop',reason=reason,charged=self.charged))
        raise BudgetStop(reason)
    def reserve(self,chain,input_upper,output_upper):
        with self.lock:
            if self.stopped:raise BudgetStop('global_stop')
            if any(type(n) is not int or n<0 for n in (input_upper,output_upper)):self.stop('invalid_bound')
            total=input_upper+output_upper
            if len(self.entries)>=self.call_limit or self.chains.get(chain,0)>=self.chain_limit or self.charged+total>self.limit:self.stop('budget_exhausted')
            key=str(len(self.entries)+1)
            event=dict(event='reserve',id=key,chain=chain,input_upper=input_upper,output_upper=output_upper,amount=total)
            try:self.persist(event)
            except BaseException:self.stopped=True;raise
            self.entries[key]=dict(event,settled=False);self.charged+=total;self.chains[chain]=self.chains.get(chain,0)+1
            return key
    def settle(self,key,usage):
        with self.lock:
            if self.stopped:raise BudgetStop('global_stop')
            row=self.entries[key]
            if row['settled']:self.stop('duplicate_settlement')
            # Unknown/malformed usage cannot release a possibly accepted send.
            if not isinstance(usage,dict):return
            p,c,t=(usage.get(k) for k in ('input_tokens','output_tokens','total_tokens'))
            if any(type(n) is not int or n<0 for n in (p,c,t)) or p+c!=t:return
            h,m=usage.get('cache_hit_tokens'),usage.get('cache_miss_tokens')
            if (h is not None or m is not None) and (any(type(n) is not int or n<0 for n in (h,m)) or h+m!=p):return
            if p>row['input_upper'] or c>row['output_upper']:self.stop('usage_exceeded_reservation')
            try:self.persist(dict(event='settle',id=key,actual=t,released=row['amount']-t))
            except BaseException:self.stopped=True;raise
            self.charged-=row['amount']-t;row['settled']=True

class GuardedAdapter:
    """Every delegate call is downstream of a bound and durable reservation.

    bound must cover the complete provider request and server-side billing
    envelope. This module does not certify an estimator. Live admission stays
    closed until that evidence exists; tests inject synthetic exact bounds.
    """
    def __init__(self,delegate,ledger,chain,bound):self.delegate=delegate;self.ledger=ledger;self.chain=chain;self.bound=bound
    async def complete(self,request):
        if request.model_id!='deepseek-flash':raise BudgetStop('flash_only')
        upper=self.bound(request) # Must fail before sending if no reliable proof.
        key=self.ledger.reserve(self.chain,upper,request.max_output_tokens)
        try:response=await self.delegate.complete(request)
        except BaseException:
            with self.ledger.lock:self.ledger.stopped=True;self.ledger.persist(dict(event='unknown_send',id=key))
            raise # Never release an uncertain reservation or retry.
        from dataclasses import asdict
        self.ledger.settle(key,None if response.usage is None else asdict(response.usage))
        return response

def live_bound_unavailable(request):
    raise BudgetStop('No verified complete provider billing-envelope token upper bound; no send')
