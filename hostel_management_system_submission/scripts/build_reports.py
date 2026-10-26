"""Build every report from real artifacts. Nothing numeric is typed by hand.

Inputs : assessment8_testing/results/{junit.xml,coverage.xml,pytest_output.txt,environment.txt,run_info.json}
         assessment9_ui/docs/browser_verification.txt   (optional, from scripts/run_browser_checks.sh)
         assessment9_ui/screenshots/manifest.json        (optional)
         docs/requirements.csv, assessment8_testing/defects.csv,
         assessment8_testing/manual_testing/{manual_test_cases.csv,manual_test_execution.csv}
Outputs: results/test_metrics.md, defect_log.md, requirements_traceability.md, final_test_report.md,
         manual_testing/manual_test_cases.md, manual_testing/manual_test_report.md,
         assessment9_ui/docs/requirement_traceability.md, assessment9_ui/screenshots/INDEX.md
Exit status 1 (and no reports) if any cited evidence is missing or failed.
"""
import collections
import csv
import datetime
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
A8 = os.path.join(ROOT, 'assessment8_testing')
A9 = os.path.join(ROOT, 'assessment9_ui')
RES = os.path.join(A8, 'results')
errors = []


def rd_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def need(path):
    if not os.path.exists(path):
        errors.append(f'missing artifact: {os.path.relpath(path, ROOT)}')
        return False
    return True


# ------------------------------------------------------------------ junit
tests = []
suite = {}
if need(os.path.join(RES, 'junit.xml')):
    root = ET.parse(os.path.join(RES, 'junit.xml')).getroot()
    ts = root if root.tag == 'testsuite' else root.find('testsuite')
    suite = {k: ts.attrib.get(k) for k in ('tests', 'failures', 'errors', 'skipped', 'time', 'timestamp')}
    for tc in ts.iter('testcase'):
        parts = tc.attrib['classname'].split('.')
        module = f'{parts[0]}/{parts[1]}.py'
        cls = parts[2:]
        nodeid = '::'.join([module] + cls + [tc.attrib['name']])
        status = 'passed'
        for tag, st in (('failure', 'failed'), ('error', 'error'), ('skipped', 'skipped')):
            if tc.find(tag) is not None:
                status = st
        tests.append(dict(nodeid=nodeid, module=module, cls=cls[0] if cls else '(module level)', name=tc.attrib['name'],
                          time=float(tc.attrib.get('time', 0)), status=status))
by_status = collections.Counter(t['status'] for t in tests)
total = len(tests)
if suite and int(suite['tests']) != total:
    errors.append(f'junit suite count {suite["tests"]} != parsed testcases {total}')

# ------------------------------------------------------------------ coverage
cov = {}
if need(os.path.join(RES, 'coverage.xml')):
    c = ET.parse(os.path.join(RES, 'coverage.xml')).getroot()
    lv, lc = int(c.attrib['lines-valid']), int(c.attrib['lines-covered'])
    bv, bc = int(c.attrib['branches-valid']), int(c.attrib['branches-covered'])
    files = []
    for cl in c.iter('class'):
        lines = cl.findall('./lines/line')
        stmts = len(lines)
        hit = sum(1 for l in lines if int(l.attrib['hits']) > 0)
        br_total = br_hit = 0
        for l in lines:
            m = re.match(r'.*\((\d+)/(\d+)\)', l.attrib.get('condition-coverage', ''))
            if m:
                br_hit += int(m.group(1)); br_total += int(m.group(2))
        files.append((cl.attrib['filename'], stmts, hit, br_total, br_hit))
    cov = dict(lines=(lc, lv), branches=(bc, bv), combined=(lc + bc, lv + bv), files=sorted(files))


def pct(a, b):
    return f'{100.0 * a / b:.1f}%' if b else 'n/a'


run_info = json.load(open(os.path.join(RES, 'run_info.json'))) if need(os.path.join(RES, 'run_info.json')) else {}
env_txt = open(os.path.join(RES, 'environment.txt'), encoding='utf-8').read() if need(os.path.join(RES, 'environment.txt')) else ''
out_txt = open(os.path.join(RES, 'pytest_output.txt'), encoding='utf-8').read() if need(os.path.join(RES, 'pytest_output.txt')) else ''
m = re.search(r'(\d+) warnings?', out_txt)
warnings_count = int(m.group(1)) if m else 0

# ------------------------------------------------------------------ browser checks
browser = []
bpath = os.path.join(A9, 'docs', 'browser_verification.txt')
if os.path.exists(bpath):
    for line in open(bpath, encoding='utf-8'):
        mm = re.match(r'^(PASS|FAIL)\s+(.*?)(\s+->.*)?$', line.rstrip())
        if mm:
            browser.append(dict(status=mm.group(1), name=mm.group(2)))
browser_fail = [b for b in browser if b['status'] == 'FAIL']


def match_tests(pattern):
    return [t for t in tests if pattern in t['nodeid']]


def check_patterns(owner, patterns):
    """Every pattern must match >=1 test and every matched test must have passed. Returns (n_tests, n_passed)."""
    seen = {}
    for p in [x.strip() for x in patterns.split(';') if x.strip()]:
        ms = match_tests(p)
        if not ms:
            errors.append(f'{owner}: cited test pattern "{p}" matches no test')
        for t in ms:
            seen[t['nodeid']] = t
            if t['status'] != 'passed':
                errors.append(f'{owner}: cited test {t["nodeid"]} is {t["status"]}')
    return len(seen), sum(1 for t in seen.values() if t['status'] == 'passed')


def check_browser(owner, patterns):
    res = []
    for p in [x.strip() for x in patterns.split(';') if x.strip()]:
        ms = [b for b in browser if p in b['name']]
        if not ms:
            errors.append(f'{owner}: cited browser check "{p}" not found in browser_verification.txt')
        for b in ms:
            if b['status'] != 'PASS':
                errors.append(f'{owner}: browser check "{b["name"]}" FAILED')
        res.append((p, len(ms), sum(1 for b in ms if b['status'] == 'PASS')))
    return res


# ------------------------------------------------------------------ registers
requirements = rd_csv(os.path.join(ROOT, 'docs', 'requirements.csv'))
defects = rd_csv(os.path.join(A8, 'defects.csv'))
cases = rd_csv(os.path.join(A8, 'manual_testing', 'manual_test_cases.csv'))
execs = rd_csv(os.path.join(A8, 'manual_testing', 'manual_test_execution.csv'))
case_ids = [c['TC-ID'] for c in cases]
if sorted(case_ids) != sorted(e['TC-ID'] for e in execs):
    errors.append('manual_test_cases.csv and manual_test_execution.csv do not list the same TC-IDs')
exec_by_id = {e['TC-ID']: e for e in execs}
VALID_STATUS = {'Not Executed', 'Pass', 'Fail', 'Blocked'}
for e in execs:
    if e['Status'] not in VALID_STATUS:
        errors.append(f'{e["TC-ID"]}: invalid Status "{e["Status"]}"')
    if e['Status'] != 'Not Executed':
        for col in ('Actual Result', 'Executed By', 'Date'):
            if not e[col].strip():
                errors.append(f'{e["TC-ID"]}: status {e["Status"]} but "{col}" is empty (results must be real, recorded values)')
    elif any(e[c].strip() for c in ('Actual Result', 'Executed By', 'Date')):
        errors.append(f'{e["TC-ID"]}: marked Not Executed but has result data')
man = collections.Counter(e['Status'] for e in execs)
man_total = len(execs)
man_done = man_total - man['Not Executed']

# requirement -> case id validation
for r in requirements:
    for cid in [x for x in r['manual_cases'].split(';') if x]:
        if cid not in case_ids:
            errors.append(f'{r["id"]}: manual case {cid} does not exist in manual_test_cases.csv')
cases_without_req = []
req_ids = {r['id'] for r in requirements}
for c in cases:
    refs = [x.strip() for x in c['Requirement'].split(',')]
    for ref in refs:
        if ref not in req_ids:
            errors.append(f'{c["TC-ID"]}: unknown requirement "{ref}"')

# defect validation
by_id = {d['id']: d for d in defects}
art_checks = {
    'DEF-029': (warnings_count == 0, f'pytest reported {warnings_count} warnings'),
    'DEF-037': (True, 'reports generated from artifacts by this script'),
    'DEF-042': (len(glob.glob(os.path.join(ROOT, '**', 'hms_app'), recursive=True)) == 1 and os.path.exists(os.path.join(ROOT, 'requirements.txt'))
                and not glob.glob(os.path.join(A8, '**', 'hms_app'), recursive=True) and not glob.glob(os.path.join(A9, '**', 'hms_app'), recursive=True),
                'exactly one hms_app package and one requirements.txt'),
    'DEF-043': (not re.search(r'flask-login|bcrypt|pytest-flask', open(os.path.join(ROOT, 'requirements.txt')).read() + open(os.path.join(ROOT, 'requirements-test.txt')).read(), re.I),
                'unused dependencies absent from requirements files'),
}
for d in defects:
    if d['status'] == 'Fixed':
        if d['verification'] == 'none':
            errors.append(f'{d["id"]}: Fixed but no verification declared')
        if d['verification'] == 'automated':
            if not (d['evidence_tests'] or d['evidence_browser']):
                errors.append(f'{d["id"]}: Fixed/automated but no evidence cited')
            if d['evidence_tests']:
                d['_n'] = check_patterns(d['id'], d['evidence_tests'])
            if d['evidence_browser']:
                check_browser(d['id'], d['evidence_browser'])
        if d['verification'] == 'artifact':
            ok, why = art_checks.get(d['id'], (False, 'no artifact check implemented'))
            if not ok:
                errors.append(f'{d["id"]}: artifact check failed ({why})')
    elif d['status'] in ('Accepted',) and d['evidence_tests']:
        check_patterns(d['id'], d['evidence_tests'])
    elif d['status'] == 'Open' and d['evidence_tests']:
        check_patterns(d['id'], d['evidence_tests'])

# requirement evidence
req_rows = []
for r in requirements:
    n, p = check_patterns(r['id'], r['automated_patterns']) if r['automated_patterns'] else (0, 0)
    br = check_browser(r['id'], r['browser_checks']) if r['browser_checks'] else []
    screens = [s for s in r['screens'].split(';') if s]
    manifest_path = os.path.join(A9, 'screenshots', 'manifest.json')
    shots = []
    if screens:
        if not os.path.exists(manifest_path):
            errors.append(f'{r["id"]}: screenshots cited but screenshots/manifest.json is missing')
        else:
            files = {s['file'] for s in json.load(open(manifest_path))['screenshots']}
            for s in screens:
                found = sorted(f for f in files if f.startswith(s + '_') or f == s + '.png')
                if not found:
                    errors.append(f'{r["id"]}: screenshot "{s}" not in manifest')
                for f in found:
                    if not os.path.exists(os.path.join(A9, 'screenshots', f)):
                        errors.append(f'{r["id"]}: screenshot file {f} missing on disk')
                shots += found
    mcs = [x for x in r['manual_cases'].split(';') if x]
    req_rows.append(dict(r=r, n=n, p=p, br=br, shots=shots, mcs=mcs))

# every screenshot referenced by a hand-written document must exist
for md in glob.glob(os.path.join(ROOT, '**', '*.md'), recursive=True):
    if 'node_modules' in md:
        continue
    for ref in re.findall(r'screenshots/([\w\-]+\.png)', open(md, encoding='utf-8').read()):
        if not os.path.exists(os.path.join(A9, 'screenshots', ref)):
            errors.append(f'{os.path.relpath(md, ROOT)} references missing screenshot {ref}')

if errors:
    print('EVIDENCE VALIDATION FAILED - no reports written:')
    for e in errors:
        print('  -', e)
    sys.exit(1)

# ------------------------------------------------------------------ helpers
now = datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')
generated_note = f'*Generated by `scripts/build_reports.py` on {now} from the artifacts in `assessment8_testing/results/`. Do not edit by hand; rerun `python scripts/run_tests.py`.*'
per_module = collections.OrderedDict()
for t in tests:
    per_module.setdefault(t['module'], collections.Counter())[t['status']] += 1
sev = collections.Counter(d['severity'] for d in defects)
stat = collections.Counter(d['status'] for d in defects)
sev_stat = collections.Counter((d['severity'], d['status']) for d in defects)
exec_time = float(suite['time'])
wall = run_info.get('wall_seconds')
tests_ok = by_status['passed'] == total and total > 0


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(text)


def md_escape(s):
    return s.replace('|', '\\|').replace('\n', '<br>')


# ------------------------------------------------------------------ test_metrics.md
L = ['# Automated test metrics', '', generated_note, '',
     f'- **Command:** `{run_info.get("command")}`',
     f'- **Started:** {run_info.get("started")}   **Exit code:** {run_info.get("exit_code")}',
     f'- **Tests:** {total}  (passed {by_status["passed"]}, failed {by_status["failed"]}, errors {by_status["error"]}, skipped {by_status["skipped"]})',
     f'- **pytest-reported test time:** {exec_time:.2f}s   **Wall time incl. coverage start-up:** {wall}s',
     f'- **Warnings:** {warnings_count}', '',
     '## Environment', '', '```', env_txt.strip(), '```', '',
     '## Tests per file', '', '| File | Tests | Passed | Failed | Errors | Skipped |', '|---|---:|---:|---:|---:|---:|']
for mod, c in per_module.items():
    L.append(f'| `{mod}` | {sum(c.values())} | {c["passed"]} | {c["failed"]} | {c["error"]} | {c["skipped"]} |')
L.append(f'| **Total** | **{total}** | **{by_status["passed"]}** | **{by_status["failed"]}** | **{by_status["error"]}** | **{by_status["skipped"]}** |')
L += ['', '## Tests per class', '', '| File | Class | Tests |', '|---|---|---:|']
cc = collections.OrderedDict()
for t in tests:
    cc[(t['module'], t['cls'])] = cc.get((t['module'], t['cls']), 0) + 1
for (mod, cls), n in cc.items():
    L.append(f'| `{mod}` | {cls} | {n} |')
L += ['', '## Coverage (`hms_app`, branch coverage on)', '',
      f'- **Statements:** {pct(*cov["lines"])}  ({cov["lines"][0]} of {cov["lines"][1]})',
      f'- **Branches:** {pct(*cov["branches"])}  ({cov["branches"][0]} of {cov["branches"][1]})',
      f'- **Combined (coverage.py "Cover" figure):** {pct(*cov["combined"])}', '',
      '| File | Statements | Covered | Branches | Covered | Cover |', '|---|---:|---:|---:|---:|---:|']
for fn, st, hit, bt, bh in cov['files']:
    L.append(f'| `{fn}` | {st} | {hit} | {bt} | {bh} | {pct(hit + bh, st + bt)} |')
L += ['', '## Ten slowest tests', '', '| Test | Seconds |', '|---|---:|']
for t in sorted(tests, key=lambda x: -x['time'])[:10]:
    L.append(f'| `{t["nodeid"]}` | {t["time"]:.2f} |')
write(os.path.join(RES, 'test_metrics.md'), '\n'.join(L) + '\n')

# ------------------------------------------------------------------ defect_log.md
L = ['# Defect log - Hostel Management System (Room Allocation module)', '', generated_note, '',
     'Source of truth: `assessment8_testing/defects.csv`. A defect is only listed as **Fixed** when the cited automated test(s) or browser check(s) exist and passed in the run summarised below.', '',
     f'**Run:** {total} tests, {by_status["passed"]} passed, {by_status["failed"] + by_status["error"]} failed/errors; browser checks: ' +
     (f'{sum(1 for b in browser if b["status"] == "PASS")}/{len(browser)} passed' if browser else 'not run'), '',
     f'## Summary: {len(defects)} defects', '', '| Severity | Fixed | Accepted | Open | Rejected | Total |', '|---|---:|---:|---:|---:|---:|']
for s in ('High', 'Medium', 'Low'):
    L.append(f'| {s} | {sev_stat[(s, "Fixed")]} | {sev_stat[(s, "Accepted")]} | {sev_stat[(s, "Open")]} | {sev_stat[(s, "Rejected")]} | {sev[s]} |')
L.append(f'| **Total** | **{stat["Fixed"]}** | **{stat["Accepted"]}** | **{stat["Open"]}** | **{stat["Rejected"]}** | **{len(defects)}** |')
cats = collections.Counter(d['category'] for d in defects)
L += ['', 'By category: ' + ', '.join(f'{k} {v}' for k, v in sorted(cats.items())), '',
      'Origin: ' + ', '.join(f'{k} {v}' for k, v in collections.Counter(d['origin'] for d in defects).items()), '',
      '## Open and accepted items', '', '| ID | Severity | Status | Title | Note |', '|---|---|---|---|---|']
for d in defects:
    if d['status'] in ('Open', 'Accepted'):
        L.append(f'| {d["id"]} | {d["severity"]} | {d["status"]} | {md_escape(d["title"])} | {md_escape(d["note"] or d["fix_summary"])} |')
L += ['', '## All defects', '']
for d in defects:
    ev = []
    if d['evidence_tests']:
        n, p = d.get('_n', (None, None))
        ev.append('tests: ' + ', '.join(f'`{x.strip()}`' for x in d['evidence_tests'].split(';')) + (f' ({p}/{n} matched tests passed)' if n is not None else ''))
    if d['evidence_browser']:
        ev.append('browser: ' + ', '.join(f'"{x.strip()}"' for x in d['evidence_browser'].split(';')))
    if d['verification'] == 'artifact':
        ev.append('artifact check: ' + art_checks[d['id']][1])
    L += [f'### {d["id"]} - {d["title"]}', f'- **Severity:** {d["severity"]} | **Status:** {d["status"]} | **Category:** {d["category"]} | **Origin:** {d["origin"]}']
    if d['fix_summary']:
        L.append(f'- **Resolution:** {d["fix_summary"]}')
    if d['files']:
        L.append(f'- **Files:** {d["files"].replace(";", ", ")}')
    if ev:
        L.append('- **Evidence:** ' + '; '.join(ev))
    if d['note']:
        L.append(f'- **Note:** {d["note"]}')
    L.append('')
write(os.path.join(A8, 'defect_log.md'), '\n'.join(L))

# ------------------------------------------------------------------ manual cases (readable) + manual report
L = ['# Manual test cases', '', '*Generated from `manual_test_cases.csv`. Record results ONLY in `manual_test_execution.csv`.*', '',
     f'{len(cases)} cases. Priority P1 = minimum set to execute; P2/P3 = recommended. Technique "UI + browser DevTools" means a developer tool (F12) is needed to tamper with a form.', '']
for mod in collections.OrderedDict.fromkeys(c['Module'] for c in cases):
    L += [f'## {mod}', '']
    for c in [c for c in cases if c['Module'] == mod]:
        L += [f'### {c["TC-ID"]} - {c["Scenario"]}', f'*Requirement:* {c["Requirement"]} | *Priority:* {c["Priority"]} | *Technique:* {c["Technique"]}', '',
              f'**Preconditions:** {c["Preconditions"] or "-"}', '', '**Steps:**', '', *[f'    {s}' for s in c['Steps'].split('\n')], '',
              f'**Input data:** {c["Input Data"] or "-"}', '', f'**Expected result:** {c["Expected Result"]}', '']
write(os.path.join(A8, 'manual_testing', 'manual_test_cases.md'), '\n'.join(L))

p1 = [c['TC-ID'] for c in cases if c['Priority'] == 'P1']
p1_done = [i for i in p1 if exec_by_id[i]['Status'] != 'Not Executed']
L = ['# Manual test execution report', '', generated_note.replace('assessment8_testing/results/', 'manual_testing/manual_test_execution.csv'), '']
if man_done == 0:
    L += ['> **STATUS: NOT EXECUTED.** No manual test case has been executed. Every result below is "Not Executed" and no actual results, testers, dates or evidence exist yet. '
          'Follow `assessment8_testing/docs/TESTING_PROCEDURE.md` section 4, record results in `manual_test_execution.csv`, then rerun `python scripts/build_reports.py`.', '']
elif man_done < man_total:
    L += [f'> **STATUS: PARTIAL.** {man_done} of {man_total} cases executed.', '']
else:
    L += [f'> **STATUS: COMPLETE.** All {man_total} cases executed.', '']
L += ['## Summary', '', '| Status | Count |', '|---|---:|']
for s in ('Pass', 'Fail', 'Blocked', 'Not Executed'):
    L.append(f'| {s} | {man[s]} |')
L += [f'| **Total** | **{man_total}** |', '', f'Priority P1: {len(p1_done)} of {len(p1)} executed.', '',
      '## Results by case', '', '| TC-ID | Priority | Scenario | Status | Executed by | Date | Defect |', '|---|---|---|---|---|---|---|']
for c in cases:
    e = exec_by_id[c['TC-ID']]
    L.append(f'| {c["TC-ID"]} | {c["Priority"]} | {md_escape(c["Scenario"])} | {e["Status"]} | {e["Executed By"] or "-"} | {e["Date"] or "-"} | {e["Defect ID"] or "-"} |')
fails = [(c, exec_by_id[c['TC-ID']]) for c in cases if exec_by_id[c['TC-ID']]['Status'] == 'Fail']
if fails:
    L += ['', '## Failed cases: actual vs expected', '']
    for c, e in fails:
        L += [f'### {c["TC-ID"]} - {c["Scenario"]}', f'- **Expected:** {c["Expected Result"]}', f'- **Actual:** {e["Actual Result"]}', f'- **Evidence:** {e["Evidence (screenshot / file)"] or "-"}', f'- **Defect:** {e["Defect ID"] or "-"}', '']
write(os.path.join(A8, 'manual_testing', 'manual_test_report.md'), '\n'.join(L) + '\n')

# ------------------------------------------------------------------ requirement traceability (A8)
def status_for(row, ui=False):
    r = row['r']
    parts = []
    if r['automated_patterns']:
        parts.append(f'{row["p"]}/{row["n"]} automated tests passed')
    else:
        parts.append('no automated test')
    if row['br']:
        parts.append(f'{sum(b[2] for b in row["br"])}/{sum(b[1] for b in row["br"])} browser checks passed')
    return '; '.join(parts)


L = ['# Assessment 8 - requirement traceability', '', generated_note, '',
     'Requirement IDs come from the shared `docs/requirements.csv` (the same IDs are used by Assessment 9). "Manual" cases are **not executed** unless the execution sheet says otherwise; this table never counts a not-executed case as evidence.', '',
     '| Req | Type | Requirement | Automated evidence | Manual cases (status) |', '|---|---|---|---|---|']
for row in req_rows:
    r = row['r']
    if r['type'] == 'UI':
        continue
    mc = ', '.join(f'{c} ({exec_by_id[c]["Status"]})' for c in row['mcs']) or '-'
    L.append(f'| {r["id"]} | {r["type"]} | {md_escape(r["statement"])} | {status_for(row)} | {mc} |')
L += ['', '## Assessment 8 PDF deliverables', '', '| # | PDF requirement | Evidence | Status |', '|---|---|---|---|',
      f'| 1 | Select a module of the project | Room Allocation module (create, reallocate, cancel, list, available rooms, student view) with its authentication/authorization | Done |',
      f'| 2 | Identify test scenarios | `docs/requirements.csv` ({sum(1 for r in requirements if r["type"] != "UI")} module requirements), `manual_testing/manual_test_cases.md` | Done |',
      f'| 3 | Prepare test cases with inputs and expected outputs | {total} automated tests; {len(cases)} manual cases with input data and expected results | Done |',
      f'| 4 | Execute test cases | Automated: {by_status["passed"]}/{total} passed (`results/junit.xml`). Manual: {man_done}/{man_total} executed | **{"Automated done; manual NOT executed" if man_done == 0 else ("Complete" if man_done == man_total else "Manual partially executed")}** |',
      '| 5 | Step-by-step procedure for manual and automated testing with a tool | `assessment8_testing/docs/TESTING_PROCEDURE.md` (pytest + coverage.py; browser + DevTools for manual) | Done |',
      f'| 6 | Record actual results, compare with expected, identify defects | `results/` artifacts; `defect_log.md` ({len(defects)} defects: {stat["Fixed"]} fixed, {stat["Open"]} open); manual actual results: {"none recorded yet" if man_done == 0 else f"{man_done} recorded"} | **{"Automated done; manual pending" if man_done < man_total else "Done"}** |',
      '| 7 | Test report summarising results and module performance | `final_test_report.md` | Done (manual section pending until executed) |']
write(os.path.join(A8, 'requirements_traceability.md'), '\n'.join(L) + '\n')

# ------------------------------------------------------------------ final test report
bp = sum(1 for b in browser if b['status'] == 'PASS')
L = ['# Final test report - Room Allocation module (Hostel Management System)', '', generated_note, '',
     '**Course:** BCSE301P Software Engineering - Assessment 8', '']
if man_done < man_total:
    L += [f'> **Completeness notice:** the automated testing is complete and its results are below. **Manual testing is NOT complete: {man_done} of {man_total} manual cases have been executed.** '
          'This report therefore does not claim that Assessment 8 is fully complete. See section 6 and `manual_testing/manual_test_report.md`.', '']
L += ['## 1. Scope and module under test', '',
      'Module: **Room Allocation** - allocating a student to a room, reallocating, cancelling, listing/searching allocations, listing available rooms, the student\'s own view, role-based access (admin, warden, student, accountant) and the authentication/CSRF/session behaviour these depend on. '
      'It is tested through the real Flask application (routes, templates, database), not through mocks.', '',
      '## 2. Test scenarios', '', f'{sum(1 for r in requirements if r["type"] != "UI")} module requirements (RA-01..) are defined in `docs/requirements.csv` and mapped to tests in `requirements_traceability.md`:', '']
for r in requirements:
    if r['type'] != 'UI':
        L.append(f'- **{r["id"]}** {r["statement"]}')
L += ['', '## 3. Test cases', '',
      f'- **Automated:** {total} pytest cases in {len(per_module)} files (table in `results/test_metrics.md`).',
      f'- **Manual:** {len(cases)} cases ({collections.Counter(c["Priority"] for c in cases)["P1"]} P1 / {collections.Counter(c["Priority"] for c in cases)["P2"]} P2 / {collections.Counter(c["Priority"] for c in cases)["P3"]} P3), each with preconditions, steps, input data and expected result (`manual_testing/manual_test_cases.md`).',
      f'- A scripted dry run (`tests/test_manual_scenarios_dry_run.py`) confirms that the manual sheet\'s expected results match the application. It is automated and is **not** manual execution evidence.', '',
      '## 4. Procedure', '', 'Full step-by-step instructions: `assessment8_testing/docs/TESTING_PROCEDURE.md`. In short:', '',
      '- **Automated** (pytest, pytest-cov, BeautifulSoup): `pip install -r requirements-test.txt` then `python scripts/run_tests.py`.',
      '- **Browser checks** (headless Chrome via puppeteer-core): `scripts/run_browser_checks.sh`.',
      '- **Manual**: start `python scripts/serve_demo.py`, follow the cases in order (see `manual_testing/Manual_Test_Document.docx`, which shows the expected screen for every case), record each result in `manual_test_execution.csv`.', '',
      '## 5. Execution results (automated)', '',
      f'Command: `{run_info.get("command")}` started {run_info.get("started")}', '',
      '| Metric | Value |', '|---|---|',
      f'| Tests run | {total} |', f'| Passed | {by_status["passed"]} |', f'| Failed | {by_status["failed"]} |', f'| Errors | {by_status["error"]} |', f'| Skipped | {by_status["skipped"]} |',
      f'| Warnings | {warnings_count} |', f'| Test time (pytest) | {exec_time:.2f}s |', f'| Wall time (incl. coverage) | {wall}s |',
      f'| Statement coverage | {pct(*cov["lines"])} ({cov["lines"][0]}/{cov["lines"][1]}) |', f'| Branch coverage | {pct(*cov["branches"])} ({cov["branches"][0]}/{cov["branches"][1]}) |',
      f'| Combined coverage | {pct(*cov["combined"])} |',
      f'| Browser checks (headless Chrome) | {f"{bp}/{len(browser)} passed" if browser else "not run"} |', '',
      'Per-file and per-class breakdowns, per-file coverage and the environment are in `results/test_metrics.md`. Raw artifacts: `results/junit.xml`, `results/coverage.xml`, `results/pytest_output.txt`.', '',
      '### Actual vs expected', '',
      (f'All {total} automated tests produced the expected outcome (actual = expected). No automated test failed in this run.' if tests_ok else
       f'**{by_status["failed"] + by_status["error"]} automated tests did not produce the expected outcome** - see `results/pytest_output.txt`.'), '',
      '## 6. Manual testing status', '',
      f'| Status | Count |', '|---|---:|'] + [f'| {s} | {man[s]} |' for s in ('Pass', 'Fail', 'Blocked', 'Not Executed')] + [
      f'| **Total** | **{man_total}** |', '',
      ('**No manual case has been executed, so there are no actual manual results to compare with the expected results.** The sheet is ready; the tester must follow `assessment8_testing/docs/TESTING_PROCEDURE.md` section 4.' if man_done == 0 else f'{man_done} cases executed; see `manual_testing/manual_test_report.md`.'), '',
      '## 7. Defects', '', f'{len(defects)} defects are registered (`defect_log.md`): **{stat["Fixed"]} fixed and verified, {stat["Open"]} open, {stat["Accepted"]} accepted, {stat["Rejected"]} rejected.**', '',
      '| Severity | Fixed | Accepted | Open | Rejected | Total |', '|---|---:|---:|---:|---:|---:|']
for s in ('High', 'Medium', 'Low'):
    L.append(f'| {s} | {sev_stat[(s, "Fixed")]} | {sev_stat[(s, "Accepted")]} | {sev_stat[(s, "Open")]} | {sev_stat[(s, "Rejected")]} | {sev[s]} |')
L += [f'| **Total** | **{stat["Fixed"]}** | **{stat["Accepted"]}** | **{stat["Open"]}** | **{stat["Rejected"]}** | **{len(defects)}** |', '', 'Open / accepted items:', '']
for d in defects:
    if d['status'] in ('Open', 'Accepted'):
        L.append(f'- **{d["id"]}** ({d["severity"]}, {d["status"]}) {d["title"]}' + (f' - {d["note"]}' if d['note'] else ''))
L += ['', '## 8. Overall assessment of the module', '',
      f'- **Functional correctness:** all {total} automated tests pass, covering allocation, reallocation, cancellation, capacity limits, validation, role-based access and dashboards.' if tests_ok else '- **Functional correctness: NOT established - automated failures exist.**',
      '- **Data integrity:** bed counters are changed with atomic conditional updates and guarded by database CHECK constraints and a partial unique index; a stale-object test reproduces the former lost-update defect and now passes.',
      '- **Security:** CSRF is enforced on every state-changing request (tested with protection enabled); logout is POST-only; login is throttled; stale sessions are handled; secure defaults and headers are tested.',
      f'- **Coverage:** {pct(*cov["combined"])} combined statement+branch coverage of `hms_app` (see `results/test_metrics.md` for uncovered files/lines).',
      '- **Limits of this evidence:** manual tests are not executed (section 6); concurrency was tested with a deterministic stale-object scenario, not with parallel load; the app was tested with SQLite only; the login throttle is per-process; browser checks ran in one engine (headless Chrome).', '',
      '## 9. Reproduction', '', '```', 'pip install -r requirements-test.txt', 'python scripts/run_tests.py          # tests, coverage, junit, reports', 'scripts/run_browser_checks.sh        # needs Node.js; see docs/TESTING_PROCEDURE.md', '```']
write(os.path.join(A8, 'final_test_report.md'), '\n'.join(L) + '\n')

# ------------------------------------------------------------------ A9 traceability + screenshot index
L = ['# Assessment 9 - requirement traceability', '', generated_note.replace('assessment8_testing/results/', 'assessment8_testing/results/ and assessment9_ui/docs/browser_verification.txt'), '',
     'Requirement IDs come from the shared `docs/requirements.csv` (RA-xx = module functions the UI must support, UI-xx = interface requirements). A requirement is marked **Verified** only if every cited automated test and browser check exists and passed. Screens link to genuine screenshots of the running application.', '',
     '| Req | Requirement | Screens | Automated tests | Browser checks | Verified |', '|---|---|---|---|---|---|']
for row in req_rows:
    r = row['r']
    if not (r['type'] == 'UI' or row['shots']):
        continue
    shots = ', '.join(f'[{s}](screenshots/{s})' for s in row['shots']) or '-'
    brs = '; '.join(f'{p}: {b}/{a}' for p, a, b in row['br']) or '-'
    verified = 'Yes' if (row['n'] == row['p'] and all(a == b for _, a, b in row['br']) and (row['n'] or row['br'])) else 'No'
    L.append(f'| {r["id"]} | {md_escape(r["statement"])} | {shots} | {row["p"]}/{row["n"]} passed | {brs} | {verified} |')
L += ['', 'Manual UI cases that remain to be executed by a person: ' + ', '.join(c['TC-ID'] for c in cases if c['TC-ID'].startswith(('UI-', 'ALLOC-15', 'CANCEL-01', 'CANCEL-02'))) + f' (status in `assessment8_testing/manual_testing/manual_test_execution.csv`: {man_done} of {man_total} executed).']
write(os.path.join(A9, 'docs', 'requirement_traceability.md'), '\n'.join(L) + '\n')

mp = os.path.join(A9, 'screenshots', 'manifest.json')
if os.path.exists(mp):
    mf = json.load(open(mp))
    L = ['# Screenshot index', '', f'*Generated from `manifest.json` (captured {mf["generated"]} from the running demo server by `scripts/browser/capture_screenshots.mjs`).*', '',
         f'{mf["count"]} screenshots: {mf["byViewport"]["desktop"]} desktop (1366x800), {mf["byViewport"]["mobile"]} mobile (390x844).', '', '| File | Viewport | Page | What it shows |', '|---|---|---|---|']
    for s in mf['screenshots']:
        if not os.path.exists(os.path.join(A9, 'screenshots', s['file'])):
            print('missing screenshot', s['file']); sys.exit(1)
        L.append(f'| [{s["file"]}]({s["file"]}) | {s["viewport"]} | `{s["url"]}` | {md_escape(s["description"])} |')
    write(os.path.join(A9, 'screenshots', 'INDEX.md'), '\n'.join(L) + '\n')

print(f'Reports built: {total} tests ({by_status["passed"]} passed), combined coverage {pct(*cov["combined"])}, {len(defects)} defects, manual {man_done}/{man_total} executed.')
