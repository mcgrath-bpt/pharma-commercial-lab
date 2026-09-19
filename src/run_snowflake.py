"""Optional cloud harness. Requires snowflake-connector-python and a named connection.

Runs only when explicitly invoked. Maintains one session for temporary Gold tables,
exports normalised CSVs and captures query IDs. Does not open evaluator truth.
"""
import argparse
import io
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from common import ROOT, read_json, write_results, write_json, GOLD_COLUMNS
from render_sql import render, safe_identifier

def normalise(value):
    if value is None:return ''
    if isinstance(value,bool):return str(value).lower()
    if isinstance(value,Decimal):return format(value.normalize(),'f')
    return value

def run(args):
    import snowflake.connector
    schema=safe_identifier(args.schema,2)
    render(args.public_root,args.stage,schema,args.out/'rendered_sql')
    manifests={m['batch_id']:m for p in args.public_root.rglob('*.manifest.json') if (m:=read_json(p))}
    evidence={'started_at':datetime.now(timezone.utc).isoformat(),'queries':[],'status':'RUNNING','checkpoints':[]}
    def execute_script(con,sql):
        for cur in con.execute_stream(io.StringIO(sql),remove_comments=True):
            evidence['queries'].append(cur.sfqid)
            cur.fetchall();cur.close()
    con=None
    try:
        con=snowflake.connector.connect(connection_name=args.connection)
        for batch in ['b001','b002']:
            if batch>args.through:break
            execute_script(con,(args.out/'rendered_sql'/f'01_load_{batch}.sql').read_text())
            cut=manifests[batch]['as_of'];datetime.fromisoformat(cut.replace('Z','+00:00'))
            sql=(ROOT/'sql/02_reference_gold.sql').read_text().replace("SET AS_OF = '2026-09-15T06:00:00Z';","SET AS_OF = '"+cut+"';")
            execute_script(con,sql)
            outputs={}
            for name,columns in GOLD_COLUMNS.items():
                with con.cursor() as cur:
                    cur.execute('SELECT '+','.join(columns)+' FROM GOLD_'+name.upper())
                    evidence['queries'].append(cur.sfqid)
                    outputs[name]=[dict(zip(columns,[normalise(v) for v in row])) for row in cur.fetchall()]
            write_results(args.out/batch,outputs);evidence['checkpoints'].append(batch)
        evidence['status']='EXECUTED_EXPORTS_READY_FOR_RECONCILIATION'
    except Exception as error:
        evidence['status']='FAILED';evidence['error_type']=type(error).__name__;raise
    finally:
        if con is not None:con.close()
        evidence['finished_at']=datetime.now(timezone.utc).isoformat();write_json(args.out/'execution.json',evidence)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--public-root',type=Path,required=True);p.add_argument('--connection',required=True);p.add_argument('--stage',required=True);p.add_argument('--schema',required=True);p.add_argument('--through',choices=['b001','b002'],default='b002');p.add_argument('--out',type=Path,required=True);run(p.parse_args())
