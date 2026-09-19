"""Render exact-file Snowflake loaders. Never creates or replaces the existing stage."""
import argparse
import re
from collections import defaultdict
from pathlib import Path
from common import read_json, sha256
from validate import validate_public

def safe_identifier(value,parts):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*){'+str(parts-1)+'}',value):
        raise ValueError('Use unquoted, fully qualified identifiers')
    return value.upper()

def lit(value):return "'"+str(value).replace("'","''")+"'"

def render(root,stage,schema,out):
    validate_public(root);stage=safe_identifier(stage,3);schema=safe_identifier(schema,2);out.mkdir(parents=True,exist_ok=True)
    sources=defaultdict(list)
    for path in sorted(root.rglob('*.manifest.json')):
        m=read_json(path);b=m['batch_id'];digest=sha256(path)
        sql=["-- Execute with a client configured to STOP on the first SQL error.",
             "-- Single loader only. Stage must expose the public_s3 tree at its URL root.",
             f"CREATE SCHEMA IF NOT EXISTS {schema};",f"USE SCHEMA {schema};",
             "ALTER SESSION SET TIMEZONE = 'UTC';",
             "CREATE FILE FORMAT IF NOT EXISTS LAB_CSV_V1 TYPE=CSV COMPRESSION=NONE FIELD_DELIMITER=',' RECORD_DELIMITER='\\n' SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='\"' ESCAPE_UNENCLOSED_FIELD=NONE EMPTY_FIELD_AS_NULL=TRUE NULL_IF=('') ERROR_ON_COLUMN_COUNT_MISMATCH=TRUE ENCODING='UTF8';",
             "CREATE TABLE IF NOT EXISTS LAB_BATCH_AUDIT (batch_id VARCHAR, manifest_sha256 VARCHAR, available_at TIMESTAMP_NTZ, loaded_at TIMESTAMP_LTZ, status VARCHAR);",
             "CREATE TABLE IF NOT EXISTS LAB_FILE_AUDIT (batch_id VARCHAR, file_key VARCHAR, expected_sha256 VARCHAR, expected_rows NUMBER, manifest_sha256 VARCHAR);",
             f"EXECUTE IMMEDIATE $$ DECLARE bad_release EXCEPTION (-20001, 'Batch ID already bound to different manifest'); n NUMBER; BEGIN SELECT COUNT(*) INTO :n FROM LAB_BATCH_AUDIT WHERE batch_id={lit(b)} AND manifest_sha256<>{lit(digest)}; IF (n>0) THEN RAISE bad_release; END IF; END; $$;"]
        for f in m['files']:
            table='RAW_'+b.upper()+'_'+f['source_entity'].replace('/','_').upper()
            columns=', '.join(safe_identifier(c,1)+' VARCHAR' for c in f['columns'])
            sql += [f"CREATE TABLE IF NOT EXISTS {table} ({columns});",
                    f"COPY INTO {table} FROM @{stage} FILES=({lit(f['key'])}) FILE_FORMAT=(FORMAT_NAME='{schema}.LAB_CSV_V1') ON_ERROR='ABORT_STATEMENT' FORCE=FALSE;",
                    f"EXECUTE IMMEDIATE $$ DECLARE bad_count EXCEPTION (-20002, 'Loaded row count differs from manifest: {table}'); n NUMBER; BEGIN SELECT COUNT(*) INTO :n FROM {table}; IF (n<>{f['row_count']}) THEN RAISE bad_count; END IF; END; $$;"]
            sources[f['source_entity']].append((table,m,f))
        # Visibility is committed only after every table has passed its count gate.
        sql+=['BEGIN TRANSACTION;']
        for f in m['files']:
            sql += [f"INSERT INTO LAB_FILE_AUDIT SELECT {lit(b)},{lit(f['key'])},{lit(f['sha256'])},{f['row_count']},{lit(digest)} WHERE NOT EXISTS (SELECT 1 FROM LAB_FILE_AUDIT WHERE batch_id={lit(b)} AND file_key={lit(f['key'])});"]
        sql += [f"INSERT INTO LAB_BATCH_AUDIT SELECT {lit(b)},{lit(digest)},TO_TIMESTAMP_NTZ({lit(m['available_at'])}),CURRENT_TIMESTAMP(),'LOADED' WHERE NOT EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT WHERE batch_id={lit(b)});",'COMMIT;']
        for name,parts in sorted(sources.items()):
            selects=[]
            for table,bm,f in parts:
                selects += [f"SELECT r.*, {lit(bm['batch_id'])} AS _batch_id, TO_TIMESTAMP_NTZ({lit(bm['available_at'])}) AS _available_at, {lit(bm['load_mode'])} AS _mode, {lit(f['key'])} AS _file_key FROM {table} r WHERE EXISTS (SELECT 1 FROM LAB_BATCH_AUDIT a WHERE a.batch_id={lit(bm['batch_id'])} AND a.status='LOADED')"]
            sql += ["CREATE OR REPLACE VIEW SRC_"+name.replace('/','_').upper()+" AS\n"+'\nUNION ALL\n'.join(selects)+';']
        (out/f'01_load_{b}.sql').write_text('\n\n'.join(sql)+'\n',encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--public-root',type=Path,required=True);p.add_argument('--stage',required=True);p.add_argument('--schema',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    render(a.public_root,a.stage,a.schema,a.out)
