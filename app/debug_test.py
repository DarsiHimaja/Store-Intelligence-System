import os, sys, traceback
sys.path.insert(0, os.path.dirname(__file__))
os.environ['DB_PATH'] = os.path.join(os.path.dirname(__file__), 'store.db')

tests = [
    ('metrics',   lambda: __import__('metrics').get_store_metrics('STORE_001')),
    ('funnel',    lambda: __import__('funnel').get_funnel('STORE_001')),
    ('heatmap',   lambda: __import__('heatmap').get_heatmap('STORE_001')),
    ('anomalies', lambda: __import__('anomalies').get_anomalies('STORE_001')),
    ('health',    lambda: __import__('health').get_health()),
]

for name, fn in tests:
    try:
        result = fn()
        print(f"[OK] {name}: {result}")
    except Exception:
        print(f"[FAIL] {name}:")
        traceback.print_exc()
    print()
