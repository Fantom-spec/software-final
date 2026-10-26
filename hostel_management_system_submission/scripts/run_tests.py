"""Run the complete automated suite with real artifacts, then rebuild the reports.

    python scripts/run_tests.py            # tests + coverage + junit + reports
    python scripts/run_tests.py --no-report

Artifacts (assessment8_testing/results/): junit.xml, coverage.xml, pytest_output.txt,
environment.txt, run_info.json. Nothing in the reports is typed by hand: scripts/build_reports.py
reads these files.
"""
import datetime
import json
import os
import platform
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RES = os.path.join(ROOT, 'assessment8_testing', 'results')
os.makedirs(RES, exist_ok=True)

cmd = [sys.executable, '-m', 'pytest', '-p', 'no:cacheprovider',
       f'--junitxml={os.path.join("assessment8_testing", "results", "junit.xml")}',
       '--cov=hms_app', '--cov-branch',
       f'--cov-report=xml:{os.path.join("assessment8_testing", "results", "coverage.xml")}',
       '--cov-report=term-missing']
started = datetime.datetime.now().astimezone()
t0 = time.perf_counter()
proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
wall = time.perf_counter() - t0
out = proc.stdout + proc.stderr
open(os.path.join(RES, 'pytest_output.txt'), 'w', encoding='utf-8').write(out)
print(out[-1800:])

freeze = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], capture_output=True, text=True).stdout.splitlines()
wanted = ('flask', 'sqlalchemy', 'werkzeug', 'wtforms', 'pytest', 'beautifulsoup4', 'python-dotenv', 'coverage')
with open(os.path.join(RES, 'environment.txt'), 'w', encoding='utf-8') as f:
    f.write(f'python: {platform.python_version()} ({platform.python_implementation()})\n')
    f.write(f'platform: {platform.platform()}\n')
    f.write('packages:\n')
    for line in freeze:
        if line.lower().startswith(wanted):
            f.write(f'  {line}\n')
json.dump({'command': ' '.join(['python', '-m', 'pytest'] + cmd[3:]), 'started': started.isoformat(timespec='seconds'),
           'wall_seconds': round(wall, 2), 'exit_code': proc.returncode},
          open(os.path.join(RES, 'run_info.json'), 'w'), indent=2)
print(f'pytest exit code {proc.returncode}, wall time {wall:.1f}s')

if '--no-report' not in sys.argv:
    rc = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'build_reports.py')], cwd=ROOT).returncode
    sys.exit(proc.returncode or rc)
sys.exit(proc.returncode)
