"""Local operator entry: inspect, or explicitly run one audited continuation.

Reuses the archived one-shot admission and original supervisor; no retry loop.
No model calls. The default action is read-only status.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REPO=Path(__file__).resolve().parents[1]
ROOT=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-full-fast-v1')
PYTHON=Path('D:/PowerTrustAI/.venv/Scripts/python.exe')
TEMPLATE_SHA='e95e3534a1b6149b0bdb818d05c785b3452b4e061f6508dceedeb60efb50ac48'


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def snapshot():
    ledger=read(ROOT/'construction-ledger.json')
    checkpoint=read(ROOT/'build/checkpoint.json')
    latest=ledger['segments'][-1]
    result=read(Path(ledger['user_authorized_extra_runs'][-1]['result']))
    return ledger,checkpoint,latest,result


def clean_pause(last,result):
    if last.get('exit_code')!=0 or result.get('exit_code')!=0:return False
    control=Path(last['control'])
    if (control/'stop.json').exists():return False
    events=[json.loads(x) for x in (control/'events.jsonl').read_text().splitlines()]
    closed=next((x for x in reversed(events) if x.get('kind')=='stage_closed'),{})
    return closed.get('primary','').startswith("PauseCheckpoint(") and closed.get('cleanup_errors')==[]


def prepare(ledger,cp,last,result):
    if time.time()>=ledger['deadline']:raise RuntimeError('原96小时期限已到，不启动。')
    if last['status']=='running' or result['status']!='finished-no-further-retry':
        raise RuntimeError('前一次仍运行或结果未完成；不得启动第二个writer。')
    paused=clean_pause(last,result)
    if result.get('failure',{}).get('kind')!='identified-managed-atomic-replace-win5' and not paused:
        raise RuntimeError('不是已识别的元数据替换故障，需要人工检查。')
    if not paused and result.get('actual_added',0)<=0:
        raise RuntimeError('故障间无新增成功提交，停止连续重试。')
    if result['after_native_committed']!=cp['count']:
        raise RuntimeError('终态与当前检查点不符，需要重新检查。')
    from evaluation.tantivy_checkpoint_recovery_v10 import dead
    control=Path(last['control'])
    dead(read(control/'process-identities.json'))
    if result.get('controller_identity'):
        d=result['controller_identity'];dead({str(d['pid']):d['created']})
    previous=Path(ledger['user_authorized_extra_runs'][-1]['result'])
    proof=previous.parent/'after-audit.json'
    a=read(proof)
    if not a.get('passed') or a['native_committed']!=cp['count']:
        raise RuntimeError('缺少本检查点的完整后验。')
    template=ROOT/'extra_resume_once_v11.py'
    if hashlib.sha256(template.read_bytes()).hexdigest()!=TEMPLATE_SHA:
        raise RuntimeError('原一次性入口模板身份变化，不执行。')
    n=max(z.get('recovery_number',0) for z in ledger['segments'])+1
    tag='user-manual-once-'+str(n)
    source=template.read_text(encoding='utf-8-sig')
    source=source.replace('import sys,os,json,time','import sys,os,json,time,psutil',1)
    source=source.replace('user-extra-once-v11',tag)
    source=source.replace("last=old['entries'][-1];dead(json.loads((ROOT/'controls/19/process-identities.json').read_text()))",
        "last=json.loads(Path("+repr(str(previous))+").read_text());dead(json.loads((Path("+repr(str(control))+ ")/'process-identities.json').read_text()))")
    source=source.replace("proof_path=Path(last['last_audit'])",'proof_path=Path('+repr(str(proof))+')')
    source=source.replace('985674',str(cp['count']))
    if paused:
        source=source.replace("last['failure']['kind']!='identified-managed-atomic-replace-win5'", "(last.get('exit_code')!=0 or last.get('status')!='finished-no-further-retry')")
    source=source.replace("'overall_attempt':4","'overall_attempt':"+str(n)).replace("p['overall_attempt']=4","p['overall_attempt']="+str(n)).replace("'recovery_number':4","'recovery_number':"+str(n))
    source=source.replace('User: 失败了 先不修复 再重新运行一次吧','Operator explicitly invoked tools.tantivy_manual_once --run-once; one attempt only')
    source=source.replace("'status':'admitted','models':0","'status':'admitted','models':0,'controller_identity':{'pid':os.getpid(),'created':psutil.Process().create_time()}")
    if "last=old['entries'][-1]" in source or "Path(last['last_audit'])" in source:
        raise RuntimeError('一次性模板接线失败，不执行。')
    path=ROOT/('manual_resume_once_'+str(n)+'.py')
    compile(source,str(path),'exec')
    return path,source,n


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-once',action='store_true',help='明确执行一次额外恢复；结束后不自动重试')
    parser.add_argument('--status',action='store_true',help='只读查看状态（默认）')
    parser.add_argument('--continue',dest='continuous',action='store_true',help='在原预算内连续执行：已识别且有新增提交的故障或已审计正常暂停后续跑')
    args=parser.parse_args()
    if args.continuous:
        if args.run_once or args.status:parser.error('--continue不能与其他动作组合')
        while True:
            ledger,cp,last,result=snapshot()
            if cp['count']==24620947:
                print('全成员已提交；仍须最终完整身份和质量验收。');return
            prepare(ledger,cp,last,result) # fail closed; no unknown failure loop
            rc=subprocess.run([str(PYTHON),'-X','utf8','-m','tools.tantivy_manual_once','--run-once'],cwd=REPO).returncode
            if rc:return rc
            time.sleep(5)
    if args.run_once and args.status:parser.error('选择--status或--run-once')
    os.chdir(REPO)
    ledger,cp,last,result=snapshot()
    print('正式已提交:',cp['count'],'/ 24620947')
    print('最近一段:',last['index'],last['status'],'/ 运行结果:',result['status'])
    print('原预算剩余小时:',round(max(0,ledger['deadline']-time.time())/3600,2))
    admission=Path(last['control'])/'worker-admission.json'
    if admission.exists():
        import psutil
        d=read(admission)
        try:alive=abs(psutil.Process(d['pid']).create_time()-d['created'])<.001
        except psutil.NoSuchProcess:alive=False
        print('最近worker:',d['pid'],'/ 当前身份匹配且存活:',alive)
    if not args.run_once:return
    path,source,n=prepare(ledger,cp,last,result)
    # Exclusive creation: repeated clicks never replace an existing admission.
    with path.open('x',encoding='utf8') as f:f.write(source)
    print('启动单次运行编号:',n,'；该命令本身就是本次额外一次执行指令。',flush=True)
    print('此窗口可能长时间无输出；另开PowerShell执行--status查看。',flush=True)
    rc=subprocess.run([str(PYTHON),'-X','utf8',str(path)],cwd=REPO).returncode
    print('本次入口已结束；请用--status读取实际结果。入口返回0也不代表建库成功。')
    return rc


if __name__=='__main__':
    try:raise SystemExit(main())
    except (RuntimeError,FileExistsError) as error:raise SystemExit(str(error))
