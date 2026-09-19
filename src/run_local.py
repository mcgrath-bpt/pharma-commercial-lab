"""Run the packaged fixture without cloud credentials or third-party Python libraries."""
import argparse
import platform
import subprocess
import sys
from pathlib import Path
from common import ROOT, read_json, write_json, write_results, sha256, GOLD_COLUMNS
from generate import generate
from reference import load_sources, calculate
from oracle import expected
from validate import validate_public, reconcile

def run(data):
    if not data.exists():generate(read_json(ROOT/'config/crawl.json'),data)
    report={'python':platform.python_version(),'snowflake_execution':'NOT_RUN','s3_upload':'NOT_RUN','public_delivery':validate_public(data/'public_s3'),'checkpoints':{}}
    for b in ['b001','b002']:
        exp=data/'private_evaluator/expected'/b;actual=ROOT/'evidence/local_actual'/b
        write_results(exp,expected(data/'private_evaluator',b))
        t,cut=load_sources(data/'public_s3',b);write_results(actual,calculate(t,cut))
        report['checkpoints'][b]=reconcile(exp,actual)
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],text=True,capture_output=True)
    (ROOT/'evidence/tests.txt').write_text(tests.stdout+tests.stderr)
    report['regression_suite_passed']=tests.returncode==0
    report['passed']=report['regression_suite_passed'] and all(r['passed'] for r in report['checkpoints'].values())
    write_json(ROOT/'evidence/validation-report.json',report)
    write_json(ROOT/'contracts/output-columns.json',GOLD_COLUMNS)
    print(report)
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=ROOT/'data');a=p.parse_args();run(a.data)
