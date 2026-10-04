"""python -m backend [--demo] [--port 8765]; always loopback, one worker."""
import argparse
from backend.config import ServiceConfig

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo',action='store_true',help='Explicit synthetic_fixture; never load .env or use paid API')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Use a local unprivileged port')
    from backend.api import create_app
    import uvicorn
    config=ServiceConfig.from_environment(demo=args.demo)
    uvicorn.run(create_app(config),host='127.0.0.1',port=args.port,workers=1,access_log=False)

if __name__=='__main__':main()
