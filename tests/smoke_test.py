import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

r = client.get('/health')
print("Health:", r.json())

r2 = client.get('/api/v1/dashboard/summary')
data = r2.json()
print("Total accounts:", data.get('total_accounts', 0))
print("Total transactions:", data.get('total_transactions', 0))
print("Active alerts:", data.get('active_alerts', 0))
print("EWS count:", data.get('ews_count', 0))

r3 = client.get('/api/v1/accounts/A102')
if r3.status_code == 200:
    acc_data = r3.json()
    print("A102 risk level:", acc_data.get('account', {}).get('current_risk_level', 'N/A'))
    print("A102 EWS count:", len(acc_data.get('ews_signals', [])))
else:
    print("A102 not found - run setup_demo.py first")
