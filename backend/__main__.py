"""python -m backend [--demo] [--port 8765]; always loopback, one worker."""
import argparse
from backend.config import ServiceConfig

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo',action='store_true',help='Explicit synthetic_fixture; never load .env or use paid API')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--open',action='store_true',help='Open local browser with a single-use local session bootstrap')
    parser.add_argument('--stop',action='store_true',help='Gracefully stop the idle localhost daily service')
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Use a local unprivileged port')
    from backend.api import create_app
    import uvicorn
    config=ServiceConfig.from_environment(demo=args.demo)
    if args.stop:
        from backend.launcher import stop_local
        stop_local(config,f'http://127.0.0.1:{args.port}')
        return
    if args.open:
        from backend.launcher import health_at,open_local
        origin=f'http://127.0.0.1:{args.port}'
        if health_at(origin):
            open_local(config,origin)
            return
        import threading
        threading.Thread(target=open_local,args=(config,origin),daemon=True).start()
    server=None
    def shutdown():server.should_exit=True
    server=uvicorn.Server(uvicorn.Config(create_app(config,shutdown=shutdown),host='127.0.0.1',port=args.port,workers=1,access_log=False))
    server.run()

if __name__=='__main__':main()
