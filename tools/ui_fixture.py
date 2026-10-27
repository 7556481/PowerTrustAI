"""Isolated synthetic UI preview: python -m tools.ui_fixture --port 8766.

No environment loader, real adapters, knowledge index or production Store.
Credentials stay internal to the temporary server and normal session bootstrap.
"""
import argparse
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import tempfile
from fastapi import Request

from agents.fakes import FakeConfig, make_fake_harness
from backend.api import create_app
from backend.assembly import Bundle, ComponentFactory
from backend.config import ServiceConfig
from core.models import AnswerDraft, CitationBinding, TaskMode, TaskRequest, VerificationStatus


class SyntheticUIFactory(ComponentFactory):
    def __init__(self, config):
        if config.profile != 'synthetic_fixture' or config.nli_enabled:
            raise ValueError('UI preview requires synthetic_fixture with NLI off')
        super().__init__(config)
        self.fake_config = FakeConfig(text='合成示例：无功支撑与电压有关。仅供界面验收，不是模型判断。')
        self.fail_next = False

    def create(self, rid, observer):
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError('synthetic_fixture deliberate assembly failure')
        harness = make_fake_harness(self.fake_config)
        harness.observer = observer
        harness.execution_path = self.config.execution_path
        return Bundle(harness)


async def terminal(service, rid):
    for _ in range(500):
        if service.state(rid)['status'] not in ('queued', 'running'):
            return
        await asyncio.sleep(.01)
    raise RuntimeError('Synthetic UI scenario did not terminate')


async def seed(service, factory):
    from uuid import uuid4
    cases = {}

    async def submit(label, fake=None, existing=False, cancel=False):
        if fake is not None:
            factory.fake_config = fake
        tid = uuid4().hex
        original = '合成初稿：无功与电压无关。'
        from agents.fakes import fake_evidence
        request = TaskRequest(tid, TaskMode.ASSESS_EXISTING if existing else TaskMode.QUESTION_ANSWER,
                              'voltage_stability_reactive_support', 'synthetic_fixture · '+label,
                              existing_answer=AnswerDraft(tid+'-answer', 1, original,
                                  citations=(CitationBinding(0,len(original),('offline-e1',)),)) if existing else None,
                              provided_evidence=(fake_evidence(),))
        rid = await service.submit(request)
        if cancel:
            for _ in range(100):
                if service.state(rid)['harness_state'] == 'verifying':
                    break
                await asyncio.sleep(.01)
            await service.cancel(rid)
        await terminal(service, rid)
        cases[label] = rid

    for i in range(17):
        await submit(f'分页记录 {i+1:02d}')
    await submit('正常答案')
    await submit('一次修订与版本1/2', FakeConfig(verification_statuses=(VerificationStatus.CONTRADICTED, VerificationStatus.SUPPORTED)), existing=True)
    await submit('资料待补充', FakeConfig(verification_statuses=(VerificationStatus.INSUFFICIENT_EVIDENCE,)))
    await submit('部分审核执行失败', FakeConfig(verification_error=True))
    factory.fail_next = True
    await submit('装配执行失败', FakeConfig())
    await submit('已取消', FakeConfig(verification_delay=1), cancel=True)
    await submit('恶意文本纯文本展示', FakeConfig(text='<script>alert(1)</script><img src=x onerror=alert(2)>'))
    factory.fake_config = FakeConfig(text='合成示例：无功支撑与电压有关。仅供界面验收，不是模型判断。', verification_delay=3)
    return cases


def fixture_app(directory, *, shutdown=None):
    directory = Path(directory).resolve()
    # Paths are supplied by this isolated entry, never from environment or API.
    config = ServiceConfig(profile='synthetic_fixture', run_db=directory/'runs.sqlite3',
                           token_file=directory/'token', index_db=directory/'unused-index.sqlite3',
                           execution_path='langgraph_v1', nli_enabled=False)
    factory = SyntheticUIFactory(config)
    factory.preflight()
    app = create_app(config, factory=factory, shutdown=shutdown)
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app):
        async with original_lifespan(app):
            app.state.fixture_cases = await seed(app.state.service, factory)
            print('synthetic_fixture ready: 24 isolated records; model requests=0; NLI off', flush=True)
            yield

    app.router.lifespan_context = lifespan

    @app.get('/fixture/connect', include_in_schema=False)
    async def connect(request: Request):
        from fastapi.responses import HTMLResponse
        # Same normal one-use ticket POST/HttpOnly session flow, only this
        # explicitly synthetic app can issue a preview bootstrap without a token UI.
        return HTMLResponse(app.state.sessions.issue(str(request.base_url).rstrip('/')))

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535 or args.port in (8765, 8770):
        parser.error('Use an isolated unprivileged port, not production/learning ports')
    import uvicorn
    with tempfile.TemporaryDirectory(prefix='powertrust-ui-') as directory:
        server = None

        def shutdown():
            server.should_exit = True

        app = fixture_app(directory, shutdown=shutdown)
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=args.port,
                                               workers=1, access_log=False, log_level='warning'))
        print(f'UI preview only: http://127.0.0.1:{args.port}/ ; connect at /fixture/connect ; Ctrl+C to release', flush=True)
        server.run()


if __name__ == '__main__':
    main()
