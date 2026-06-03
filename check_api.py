import requests, json, sys

store = 'STORE_001'
base = 'http://localhost:8000'

endpoints = [
    '/health',
    f'/stores/{store}/metrics',
    f'/stores/{store}/funnel',
    f'/stores/{store}/heatmap',
    f'/stores/{store}/anomalies',
]

all_ok = True
for ep in endpoints:
    try:
        r = requests.get(base + ep, timeout=3)
        data = r.json()
        print(f"[{r.status_code}] {ep}")
        print(f"       {json.dumps(data)[:150]}")
    except Exception as e:
        print(f"[ERR] {ep}: {e}")
        all_ok = False

print()
print("ALL OK" if all_ok else "ERRORS FOUND")
