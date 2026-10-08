import json, urllib.request
BASE='http://127.0.0.1:5000'

def get(path):
    with urllib.request.urlopen(BASE+path,timeout=5) as r:
        return r.status, json.loads(r.read().decode())

for path in ['/api/health','/api/tools','/api/stats']:
    status, data=get(path)
    print(path, status, 'OK' if data.get('ok') else 'FAIL')

payload={'tool':'meeting','mode':'action-items','input':'Team agreed that the demo is Friday. Samip handles UI. Sandeed handles DB. Test API tonight.'}
req=urllib.request.Request(BASE+'/api/ai',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
with urllib.request.urlopen(req,timeout=10) as r:
    data=json.loads(r.read().decode())
print('/api/ai',r.status,'OK' if data.get('ok') and data.get('id') else 'FAIL',data.get('provider'))
