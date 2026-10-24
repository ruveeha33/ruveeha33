"""Run alongside a NuclearShield checkout; uses only bundled synthetic evidence."""
from pathlib import Path
import os, sys, json, hashlib, tempfile

root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(root))
os.environ['NUCLEARSHIELD_DATA_DIR'] = tempfile.mkdtemp(prefix='nuclearshield-portfolio-')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
results = []
for name in ['NuclearShield-Full-Platform-100-Records.jsonl', 'NuclearShield-IsolationForest-80-Network-Records.csv']:
    source = root / 'sample-data' / name
    raw = source.read_bytes()
    before = hashlib.sha256(raw).hexdigest()
    created = client.post('/api/ingest', files={'file': (name, raw, 'application/octet-stream')})
    assert created.status_code == 200, created.text
    analysis_id = created.json()['analysis_id']
    detail = client.get(f'/api/analyses/{analysis_id}')
    assert detail.status_code == 200
    payload = detail.json()
    results.append({'fixture': name, 'input_sha256': before, 'source_unchanged': before == hashlib.sha256(source.read_bytes()).hexdigest(), 'detail': payload})
    if name.endswith('.jsonl'):
        report = client.get(f'/api/report/download?analysis_id={analysis_id}')
        assert report.status_code == 200
        (out/'nuclearshield-generated-report.html').write_bytes(report.content)
(out/'nuclearshield-results.json').write_text(json.dumps(results, indent=2))
print(json.dumps([{'fixture': r['fixture'], 'source_unchanged': r['source_unchanged'], 'event_count': r['detail'].get('event_count'), 'summary': r['detail'].get('summary')} for r in results]))
