from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from fastapi.testclient import TestClient
from cupnavi_api.main import app

response=TestClient(app).get("/health")
assert response.status_code==200
payload=response.json()
for key in ("ok","version","database_backend","database_ok","database_latency_ms"):
    assert key in payload,key
assert isinstance(payload["database_latency_ms"],(int,float))
print(payload)
