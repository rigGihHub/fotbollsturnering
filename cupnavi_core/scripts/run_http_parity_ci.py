from __future__ import annotations
from pathlib import Path
import os, sys, subprocess, time, urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

ROOT=Path(__file__).resolve().parents[1]
port=os.getenv("CUPNAVI_HTTP_PARITY_PORT","8766")
env=os.environ.copy()
env["CUPNAVI_HTTP_BASE_URL"]=f"http://127.0.0.1:{port}"

proc=subprocess.Popen(
    [sys.executable,"-m","uvicorn","cupnavi_api.main:app","--host","127.0.0.1","--port",port],
    cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,
)
try:
    deadline=time.time()+25
    health=f"http://127.0.0.1:{port}/health"
    while time.time()<deadline:
        try:
            with urllib.request.urlopen(health,timeout=2) as resp:
                if resp.status==200:
                    break
        except Exception:
            time.sleep(.5)
    else:
        raise RuntimeError("API did not become healthy")

    result=subprocess.run(
        [sys.executable,"scripts/check_http_public_parity.py"],
        cwd=ROOT,env=env,text=True,capture_output=True,timeout=30,
    )
    print(result.stdout,end="")
    if result.stderr:
        print(result.stderr,file=sys.stderr,end="")
    raise SystemExit(result.returncode)
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
