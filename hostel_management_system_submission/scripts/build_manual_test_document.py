"""Build the Manual Test Document (.docx, plus .pdf if LibreOffice is available).

    python scripts/build_manual_test_document.py

Inputs : assessment8_testing/manual_testing/manual_test_cases.csv      (cases)
         assessment8_testing/manual_testing/manual_test_execution.csv  (results - filled in by the human tester)
         assessment8_testing/manual_testing/reference_screenshots/      (script-captured EXPECTED states)
         assessment8_testing/manual_testing/evidence/                   (the tester's own screenshots, optional)
Output : assessment8_testing/manual_testing/Manual_Test_Document.docx  (+ .pdf)

The document never marks a case as executed unless the execution sheet says so. Reference screenshots are labelled
as script-captured and are never presented as tester evidence.
Needs: Node.js and the npm package `docx`  (cd scripts/browser && npm install).
"""
import csv
import datetime
import json
import os
import shutil
import struct
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MT = os.path.join(ROOT, 'assessment8_testing', 'manual_testing')
REF = os.path.join(MT, 'reference_screenshots')
EVD = os.path.join(MT, 'evidence')
sys.path.insert(0, ROOT)


def jpeg_size(path):
    with open(path, 'rb') as f:
        data = f.read()
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II', data[16:24])
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack('>HH', data[i + 5:i + 9])
            return w, h
        i += 2 + struct.unpack('>H', data[i + 2:i + 4])[0]
    raise ValueError(path)


def rd(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


cases = rd(os.path.join(MT, 'manual_test_cases.csv'))
execs = {e['TC-ID']: e for e in rd(os.path.join(MT, 'manual_test_execution.csv'))}
manifest = json.load(open(os.path.join(REF, 'reference_manifest.json')))
errors = []
out_cases = []
for c in cases:
    cid = c['TC-ID']
    e = execs.get(cid)
    if not e:
        errors.append(f'{cid}: no row in manual_test_execution.csv')
        continue
    refs = []
    for s in manifest['cases'].get(cid, []):
        p = os.path.join(REF, s['file'])
        if not os.path.exists(p):
            errors.append(f'{cid}: reference screenshot {s["file"]} missing')
            continue
        w, h = jpeg_size(p)
        refs.append(dict(abs=p, caption=s['caption'], w=w, h=h))
    if not refs:
        errors.append(f'{cid}: no reference screenshot')
    evidence = None
    ev_name = (e.get('Evidence (screenshot / file)') or '').strip()
    if e['Status'] != 'Not Executed' and ev_name:
        ep = os.path.join(EVD, ev_name)
        if os.path.exists(ep):
            w, h = jpeg_size(ep)
            evidence = dict(abs=ep, w=w, h=h, name=ev_name)
        else:
            errors.append(f'{cid}: evidence file "{ev_name}" not found in manual_testing/evidence/')
    out_cases.append(dict(
        id=cid, module=c['Module'], requirement=c['Requirement'], technique=c['Technique'], priority=c['Priority'],
        scenario=c['Scenario'], preconditions=c['Preconditions'], steps=[s for s in c['Steps'].split('\n') if s.strip()],
        input=c['Input Data'], expected=c['Expected Result'],
        result=dict(status=e['Status'], actual=e['Actual Result'], evidenceName=ev_name, defect=e['Defect ID'], by=e['Executed By'], date=e['Date'], build=e['Build / commit tested']),
        ref=refs, evidence=evidence))
if errors:
    print('Cannot build the document:')
    for x in errors:
        print('  -', x)
    sys.exit(1)

# ---- test data straight from the application's own demo seed (no hand-typed copies)
from tests.helpers import make_app            # noqa: E402
from hms_app.models import User, Student, Room  # noqa: E402
app = make_app(SEED_DEMO_DATA=True)
with app.app_context():
    students = [dict(id=s.student_id, name=s.user.name, email=s.user.email, roll=s.roll_no, course=s.course or '', batch=s.batch or '')
                for s in Student.query.order_by(Student.student_id).all()]
    rooms = [dict(id=r.room_id, block=r.block.name, number=r.room_number, floor=r.floor, capacity=r.capacity)
             for r in Room.query.order_by(Room.room_id).all()]
    accounts = [dict(role=u.role, email=u.email) for u in User.query.filter(User.role != 'student').order_by(User.user_id).all()]
passwords = {'admin': 'admin123', 'warden': 'warden123', 'accountant': 'accountant123'}
for a in accounts:
    a['password'] = passwords[a['role']]

counts = {s: sum(1 for c in out_cases if c['result']['status'] == s) for s in ('Pass', 'Fail', 'Blocked', 'Not Executed')}
data = dict(generated=datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z'), counts=counts, total=len(out_cases),
            refCaptured=manifest['generated'], cases=out_cases, students=students, rooms=rooms, accounts=accounts)
tmp = os.path.join(MT, '.manual_doc_data.json')
json.dump(data, open(tmp, 'w'), indent=1)
docx_path = os.path.join(MT, 'Manual_Test_Document.docx')
node = shutil.which('node')
if not node:
    print('Node.js is required to build the .docx'); sys.exit(1)
env = dict(os.environ, NODE_PATH=os.pathsep.join([os.path.join(ROOT, 'scripts', 'browser', 'node_modules'), os.environ.get('NODE_PATH', '')]))
rc = subprocess.run([node, os.path.join(ROOT, 'scripts', 'build_manual_test_document.js'), tmp, docx_path], env=env).returncode
os.remove(tmp)
if rc:
    sys.exit(rc)
print(f'Wrote {os.path.relpath(docx_path, ROOT)}  ({counts["Not Executed"]} of {len(out_cases)} cases not executed)')
soffice = shutil.which('soffice') or shutil.which('libreoffice')
if soffice:
    subprocess.run([soffice, '--headless', '--convert-to', 'pdf', '--outdir', MT, docx_path], capture_output=True)
    if os.path.exists(os.path.join(MT, 'Manual_Test_Document.pdf')):
        print('Wrote assessment8_testing/manual_testing/Manual_Test_Document.pdf')
