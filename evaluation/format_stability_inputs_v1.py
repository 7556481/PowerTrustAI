"""Four synthetic development tasks; offline only, no model client."""
from copy import deepcopy

from evaluation import premise_bound_review_v6 as v6, premise_bound_review_v7 as v7
from evaluation.text_bound_review import canonical, sha


def build():
    definitions = [
        ('FMT-01', '按合成目录约定说明柚签是什么、用来做什么。',
         ['说明类别','说明用途'], '柚签是一种目录标记，用于标出待复核条目。',
         '柚签属于目录标记，用于标出待复核条目。'),
        ('FMT-02', '按合成玩具钟规则说明蓝色模式的步长及适用范围。',
         ['说明每次步长','保留适用沙盘范围'],
         '蓝色模式每次前进两格；该规则仅适用于沙盘S。',
         '蓝色模式每次前进三格。该规则仅适用于沙盘S。'),
        ('FMT-03', '根据合成图书馆约定说明松纹牌的用途，不推测借阅权限。',
         ['说明标记的用途','保留待修状态限定'],
         '松纹牌用于标记待修图书；这段约定不说明借阅权限。',
         '松纹牌标记待修图书，持牌者还可无限借阅所有馆藏。'),
        ('FMT-04', '假定标本K属于软封类。按合成规则说明本题接收条件，并说明适用前提，不作现实验收结论。',
         ['说明本题假定的类别','说明接收窗口条件'],
         '软封类样品仅在窗口T内接收。',
         '按本题假定，标本K属于软封类。按规则，仅在窗口T内接收它。'),
    ]
    tasks = []
    for sid, question, requirements, text, answer in definitions:
        spans = []
        if sid == 'FMT-04':
            start = question.index('标本K属于软封类')
            spans = [{'start':start,'end':start+len('标本K属于软封类')}]
        card = {'question':question,'premise_spans':spans,
            'requirements':[{'id':'R'+str(i+1),'model_visible_task_requirement':r}
                            for i,r in enumerate(requirements)],
            'evidence':[{'id':sid+'-E1','text':text,'url':'synthetic://'+sid,
                         'locator':'synthetic-rule-v1','text_basis':'constructed development rule'}]}
        tasks.append(v6.model_input(card, {'id':sid,'answer':answer}))
    return tasks


def prepare(tasks):
    if tasks != build():
        raise ValueError('Only the fixed four synthetic tasks are allowed')
    if v6.parse is not v7.parse:
        raise ValueError('Identical acceptance parser required')
    order = []
    for i, task in enumerate(tasks):
        arms = ('v6','v7') if i % 2 == 0 else ('v7','v6')
        pair = {}
        for arm, protocol in [('v6',v6),('v7',v7)]:
            messages = [{'role':m.role,'content':m.content} for m in protocol.messages(task)]
            pair[arm] = messages
        if pair['v6'][1:] != pair['v7'][1:]:
            raise ValueError('Task messages must be identical across arms')
        for arm in arms:
            order.append({'request_id':task['sample_id']+'-'+arm,
                          'sample_id':task['sample_id'],'arm':arm,
                          'task_sha256_utf8':sha(canonical(task).encode()),
                          'messages_sha256_utf8':sha(canonical(pair[arm]).encode())})
    return deepcopy(order)
