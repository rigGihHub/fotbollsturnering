from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
PWA=ROOT/"public_pwa"
errors=[]

manifest=json.loads((PWA/"manifest.webmanifest").read_text(encoding="utf-8"))
for key in ("name","short_name","start_url","scope","display","theme_color"):
    if not manifest.get(key):
        errors.append(f"manifest missing {key}")
if manifest.get("display")!="standalone":
    errors.append("manifest display must be standalone")

sw=(PWA/"service-worker.js").read_text(encoding="utf-8")
for required in ('addEventListener("install"','addEventListener("fetch"',"manifest.webmanifest","app.js","styles.css",'req.mode==="navigate"','caches.match("./index.html")'):
    if required not in sw:
        errors.append(f"service worker missing {required}")

html=(PWA/"index.html").read_text(encoding="utf-8")
if 'rel="manifest"' not in html:
    errors.append("index.html has no manifest link")
if 'meta name="theme-color"' not in html:
    errors.append("index.html has no theme-color")

if errors:
    print("\n".join("FAIL: "+x for x in errors))
    raise SystemExit(2)
print("PWA installability contract: OK")
