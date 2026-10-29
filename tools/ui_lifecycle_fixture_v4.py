"""v4 browser acceptance atop ui_fixture; synthetic only, no public fault switches."""
import argparse
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
import tempfile
from uuid import uuid4

from core.models import TaskRequest,TaskMode
from tools.ui_fixture import fixture_app,SyntheticUIFactory


class LifecyclePreviewFactory(SyntheticUIFactory):
    def __init__(self,config):super().__init__(config);self.next_mode='normal'

    def create(self,rid,observer):
        bundle=super().create(rid,observer);mode=self.next_mode;self.next_mode='normal'
        if mode=='no_answer':
            original=bundle.harness.generation.run
            async def generate(inputs):
                value=await original(inputs)
                return replace(value,substantive_answer=False,answer=replace(value.answer,
                    text='合成示例：资料不足，未生成实质回答。',missing_information=('请补充问题所需来源。',)))
            bundle.harness.generation.run=generate
        if mode=='close_error':
            def close():raise RuntimeError('synthetic close fault')
            bundle.close=close
        return bundle


def lifecycle_fixture(directory,*,cleanup_fault_on_next=False):
    app=fixture_app(directory);parent=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(app):
        async with parent(app):
            service=app.state.service;factory=LifecyclePreviewFactory(service.config);service.factory=factory
            factory.next_mode='no_answer'
            rid=await service.submit(TaskRequest(uuid4().hex,TaskMode.QUESTION_ANSWER,'voltage_stability_reactive_support','synthetic_fixture · 正常无实质回答'))
            import asyncio
            await asyncio.wait_for(service.queue.join(),5)
            app.state.lifecycle_no_answer=rid
            factory.next_mode='close_error' if cleanup_fault_on_next else 'normal'
            print('v4 synthetic lifecycle fixture ready; model requests=0; no-answer seeded',flush=True)
            yield
    app.router.lifespan_context=lifespan
    return app


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cleanup-fault-on-next',action='store_true')
    args=parser.parse_args()
    import uvicorn
    with tempfile.TemporaryDirectory(prefix='powertrust-lifecycle-ui-') as directory:
        uvicorn.run(lifecycle_fixture(Path(directory),cleanup_fault_on_next=args.cleanup_fault_on_next),
                    host='127.0.0.1',port=8766,access_log=False,log_level='warning')


if __name__=='__main__':main()
