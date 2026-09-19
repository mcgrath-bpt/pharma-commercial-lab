"""AWS CLI uploader. Dry run by default; only the validated public tree is eligible.

Writes data first, manifests next and each ready marker last. Conditional puts
refuse overwrite. Resume verifies the remote SHA-256, never assumes ETag is SHA.
"""
import argparse
import base64
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from common import sha256, read_json
from validate import validate_public

def upload(root,uri,execute=False):
    root=root.resolve()
    if root.name!='public_s3':raise ValueError('Point explicitly at the public_s3 directory')
    validate_public(root)
    parsed=urlparse(uri)
    if parsed.scheme!='s3' or not parsed.netloc or parsed.query or parsed.fragment:raise ValueError('Expected stage URL s3://bucket/optional-prefix/')
    files=list(root.rglob('*'));files=[f for f in files if f.is_file()]
    allowed=set()
    for manifest_path in root.rglob('*.manifest.json'):
        manifest=read_json(manifest_path)
        allowed.update((root/f['key']).resolve() for f in manifest['files'])
        allowed.update(p.resolve() for p in [manifest_path,manifest_path.with_name(manifest['batch_id']+'.ready.json'),manifest_path.parent/'source-contracts.json'])
        receipt_path=manifest_path.parent/'territory-adapter.receipt.json'
        if receipt_path.exists():
            workbook=manifest_path.parent.parent/'business_files/territory/territory_mapping_202609.xlsx'
            receipt=read_json(receipt_path)
            if sha256(workbook)!=receipt['input_sha256']:raise ValueError('Workbook fingerprint mismatch')
            territory=next(f for mp in root.rglob('*.manifest.json') for f in read_json(mp)['files'] if f['source_entity']=='manual/territory_mapping')
            if receipt['output_sha256']!=territory['sha256']:raise ValueError('Adapter CSV fingerprint mismatch')
            allowed.update([receipt_path.resolve(),workbook.resolve()])
    if allowed!={f.resolve() for f in files}:raise ValueError('Unlisted or missing file in upload tree')
    def order(f):
        return (2 if f.name.endswith('.ready.json') else 1 if f.name.endswith('.manifest.json') else 0,str(f))
    for f in sorted(files,key=order):
        if not f.resolve().is_relative_to(root):raise ValueError('Symlink escapes public tree')
        key='/'.join(x for x in [parsed.path.strip('/'),str(f.relative_to(root))] if x)
        digest=base64.b64encode(bytes.fromhex(sha256(f))).decode()
        if not execute:
            print('Would upload',f.relative_to(root),'to',f's3://{parsed.netloc}/{key}');continue
        cmd=['aws','s3api','put-object','--bucket',parsed.netloc,'--key',key,'--body',str(f),'--checksum-sha256',digest,'--if-none-match','*','--no-cli-pager']
        result=subprocess.run(cmd,capture_output=True,text=True)
        if result.returncode:
            if 'PreconditionFailed' not in result.stderr and '412' not in result.stderr:raise RuntimeError(result.stderr)
            head=subprocess.run(['aws','s3api','head-object','--bucket',parsed.netloc,'--key',key,'--checksum-mode','ENABLED','--no-cli-pager'],capture_output=True,text=True,check=True)
            if json.loads(head.stdout).get('ChecksumSHA256')!=digest:raise ValueError('Existing object differs or checksum unavailable: '+key)
        print('Verified uploaded or identical:',key)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--public-root',type=Path,required=True);p.add_argument('--stage-url',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    upload(a.public_root,a.stage_url,a.execute)
