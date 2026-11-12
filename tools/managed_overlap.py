"""Daily managed launcher; configuration absent means ordinary ComponentFactory."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import time
import threading
from backend.config import ROOT, ServiceConfig
from backend.launcher import health_at, open_local, stop_local
from backend.managed import ManagedFactory


def read_managed(path):
    path = Path(path)
    if not path.exists():
        return dict(version='local-managed-service-v25', factory='component', port=8765)
    value = json.loads(path.read_text(encoding='utf-8'))
    if (set(value) - {'version', 'factory', 'port', 'run_db', 'token_file'} or
        value.get('version') != 'local-managed-service-v25' or
        value.get('factory') not in ('component', 'overlap') or
        type(value.get('port')) is not int or not 1024 <= value['port'] <= 65535):
        raise ValueError('Invalid local managed service configuration')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'data/runtime_local/managed-service.json')
    parser.add_argument('--port', type=int)
    parser.add_argument('--factory', choices=('component', 'overlap'))
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--no-open', action='store_true')
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    managed = read_managed(args.config)
    port = args.port if args.port is not None else managed['port']
    if not 1024 <= port <= 65535:
        parser.error('Unprivileged local port required')
    config = ServiceConfig.from_environment()
    config = replace(config, **{key:Path(managed[key]).resolve() for key in ('run_db', 'token_file') if key in managed})
    selected = args.factory or managed['factory']
    origin = f'http://127.0.0.1:{port}'
    current = health_at(origin)
    if args.stop or args.rollback:
        if current:
            stop_local(config, origin)  # Original idle/queue/drain guard; never kill.
            deadline = time.monotonic() + 30
            while health_at(origin) and time.monotonic() < deadline:
                time.sleep(.1)
            if health_at(origin):
                raise RuntimeError('Graceful stop did not finish; configuration unchanged')
        if not args.rollback:
            return
        managed['factory'] = 'component'
        args.config.parent.mkdir(parents=True, exist_ok=True)
        pending = args.config.with_suffix('.pending')
        pending.write_text(json.dumps(managed, ensure_ascii=False, indent=2), encoding='utf-8')
        pending.replace(args.config)
        selected = 'component'
        current = None
    if current:
        actual = current.get('managed_factory') or {}
        if (actual.get('selection') != selected or
            actual.get('run_db') != str(config.run_db.resolve()) or
            actual.get('startup_factory_probe_enabled') != (selected == 'overlap')):
            raise RuntimeError('Existing server identity/Factory differs; stop it gracefully before switching')
        if args.open and not args.no_open:
            open_local(config, origin)
        return
    from backend.api import create_app
    import uvicorn
    if args.open and not args.no_open:
        threading.Thread(target=open_local, args=(config, origin), daemon=True).start()
    server = None
    def shutdown():
        server.should_exit = True
    server = uvicorn.Server(uvicorn.Config(
        create_app(config, factory=ManagedFactory(config, selected), shutdown=shutdown),
        host='127.0.0.1', port=port, workers=1, access_log=False))
    server.run()


if __name__ == '__main__':
    main()
