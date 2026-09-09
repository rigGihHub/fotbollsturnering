from __future__ import annotations
import os, sys, json, ssl, urllib.request
from urllib.parse import urlparse

BASE=os.getenv("CUPNAVI_STAGING_BASE_URL","").strip().rstrip("/")
CUP=os.getenv("CUPNAVI_PARITY_CUP","").strip()

def fetch(path):
    req=urllib.request.Request(BASE+path,headers={"User-Agent":"CupNavi-Staging-Check/157"})
    with urllib.request.urlopen(req,timeout=12) as resp:
        return resp.status,dict(resp.headers),resp.read()

def main():
    if not BASE:
        print("SKIP: CUPNAVI_STAGING_BASE_URL is not set.")
        return 0
    parsed=urlparse(BASE)
    if parsed.scheme!="https":
        print("FAIL: staging URL must use HTTPS")
        return 2

    status,headers,body=fetch("/health")
    if status!=200:
        print("FAIL: /health not 200"); return 3
    health=json.loads(body.decode())
    if not health.get("ok"):
        print("FAIL: health not OK"); return 4

    status,headers,body=fetch("/manifest.webmanifest")
    if status!=200:
        print("FAIL: manifest missing"); return 5
    manifest=json.loads(body.decode())
    if manifest.get("display")!="standalone":
        print("FAIL: manifest not standalone"); return 6

    status,headers,body=fetch("/service-worker.js")
    if status!=200 or b'addEventListener("fetch"' not in body:
        print("FAIL: service worker invalid"); return 7

    # Security headers from the reverse proxy.
    status,headers,body=fetch("/")
    lower={k.lower():v for k,v in headers.items()}
    required=("x-content-type-options","x-frame-options","referrer-policy")
    missing=[k for k in required if k not in lower]
    if missing:
        print("FAIL: missing security headers:",",".join(missing)); return 8

    if CUP:
        status,_,body=fetch(f"/api/public/cups/{CUP}")
        if status!=200:
            print("FAIL: public cup endpoint unavailable"); return 9

    print(json.dumps({
        "ok":True,
        "base_url":BASE,
        "https":True,
        "health":health,
        "manifest":True,
        "service_worker":True,
        "security_headers":True,
        "cup_checked":bool(CUP),
    },ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
