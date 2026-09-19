"""Optional private canonical hydration into a new empty evaluator schema.

The normal oracle runs locally; this loader is only needed if evaluator truth
must also be available in Snowflake. Never run with the builder connection.
"""
import argparse
from pathlib import Path
from common import ROOT, read_json, read_csv, sha256
from model import definitions
from render_sql import safe_identifier

def hydrate(args):
    import snowflake.connector
    import io
    schema=safe_identifier(args.schema,2)
    manifest=read_json(args.private_root/'canonical-manifest.json')
    for f in manifest['files']:
        path=args.private_root/f['path']
        if sha256(path)!=f['sha256'] or len(read_csv(path))!=f['row_count']:raise ValueError('Private file integrity mismatch')
    with snowflake.connector.connect(connection_name=args.connection) as con:
        sql=(ROOT/'sql/00_canonical_private.sql').read_text().replace('SYNTH_TRUTH',schema)
        for cur in con.execute_stream(io.StringIO(sql),remove_comments=True):cur.fetchall();cur.close()
        with con.cursor() as cur:
            for table in definitions():
                cur.execute('SELECT COUNT(*) FROM '+table)
                if cur.fetchone()[0]!=0:raise ValueError('Use an empty evaluator schema; refusing to append to '+table)
            cur.execute('BEGIN TRANSACTION')
            try:
                for table,spec in definitions().items():
                    def convert(row):
                        values=[]
                        for c in spec['columns']:
                            v=row[c['name']]
                            values.append(None if v=='' else int(v) if c['type']=='NUMBER' else v.lower()=='true' if c['type']=='BOOLEAN' else v)
                        return tuple(values)
                    rows=[convert(r) for r in read_csv(args.private_root/'canonical'/f'{table}.csv')]
                    cols=','.join(c['name'] for c in spec['columns'])
                    placeholders=','.join(['%s']*len(spec['columns']))
                    cur.executemany(f'INSERT INTO {table} ({cols}) VALUES ({placeholders})',rows)
                cur.execute('COMMIT')
            except Exception:
                cur.execute('ROLLBACK');raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);p.add_argument('--connection',required=True);p.add_argument('--schema',required=True);hydrate(p.parse_args())
