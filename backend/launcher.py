"""Normal localhost launcher. No credential output and no duplicate server."""
import json
from pathlib import Path
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
import webbrowser
from backend.local_access import token_for


def health_at(origin):
    try:
        with urlopen(origin+'/health',timeout=2) as response:return json.load(response)
    except URLError:return None


def open_local(config, origin, *, opener=webbrowser.open):
    deadline=time.monotonic()+40
    while time.monotonic()<deadline:
        health=health_at(origin)
        if health:
            if health.get('local_session_version')!='localhost-launch-session-v1' or health.get('profile')!=config.profile:
                raise RuntimeError('此端口已有不同版本或模式的服务，请在原终端正常停止后重启。')
            # Existing server exclusively reads the same fixed server token.
            request=Request(origin+'/session/launch',data=b'{}',method='POST',headers={
                'Authorization':'Bearer '+token_for(config.token_file),'Content-Type':'application/json'})
            with urlopen(request,timeout=5) as response:bootstrap=json.load(response)['html']
            path=Path(config.token_file).parent/'local-session-bootstrap.html'
            path.write_text(bootstrap,encoding='utf-8')
            opener(path.resolve().as_uri())
            return
        time.sleep(.2)
    raise RuntimeError('本机服务启动超时；查看终端提示，不自动重发任务。')


def stop_local(config, origin):
    request=Request(origin+'/session/stop',data=b'{}',method='POST',headers={
        'Authorization':'Bearer '+token_for(config.token_file),'Content-Type':'application/json'})
    with urlopen(request,timeout=5) as response:json.load(response)
