"""Deterministic canonical world, imperfect projections and private evaluation ledger."""
import argparse
import copy
import hashlib
import random
import re
from datetime import date, timedelta
from pathlib import Path
from common import ROOT, read_json, write_json, write_csv, sha256
from model import definitions, export

def generate(config, dest):
    if dest.exists() and any(dest.iterdir()):
        raise ValueError("Destination must be empty. Use a new release directory; never overwrite a delivery.")
    n, count = config["hcp_count"], config["interaction_count"]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',config['release_id']):
        raise ValueError('Release identity must be a safe single path component')
    if n < 100 or count < 300 or len(config["batches"]) != 2:
        raise ValueError("v0.1 requires >=100 HCPs, >=300 interactions and the two defined batches")
    if [b['id'] for b in config['batches']] != ['b001','b002'] or config['late_arrival_days'] != 7:
        raise ValueError('v0.1 fixture schedule requires b001/b002 and seven days')
    if config['history_start'] != '2026-07-01' or config['history_end'] != '2026-09-13':
        raise ValueError('v0.1 fixed-calendar boundary fixtures require July–September 2026')
    if [b['available_at'][:10] for b in config['batches']] != ['2026-09-14','2026-09-15']:
        raise ValueError('v0.1 fixed-calendar delivery dates required')
    if config['reporting_timezone'] != 'UTC':
        raise ValueError('v0.1 uses UTC; do not silently reinterpret calendar dates')
    rng = random.Random(config["seed"])
    world = {name:[] for name in definitions()}
    identities = {}
    def ident(kind, i, source):
        key = (kind,i,source)
        if key not in identities:
            sid = source[:2].upper()+"_"+hashlib.sha256(f"{config['seed']}|{kind}|{i}|{source}".encode()).hexdigest()[:14]
            identities[key] = sid
            world['source_identity'].append(dict(entity_type=kind,canonical_id=f"{kind.upper()}-{i:06}",source=source,source_id=sid,link_token=token(kind,i)))
        return identities[key]
    def token(kind, i):
        return "SYN_"+hashlib.sha256(f"LINK|{config['seed']}|{kind}|{i}".encode()).hexdigest()[:16]
    def cid(kind,i): return f"{kind.upper()}-{i:06}"
    for i in range(1,13):
        world['hco'].append(dict(hco_id=cid('hco',i),organisation_name=f"Synthetic Organisation {i:03}",country=config['country']))
    for i in range(1,n+1):
        world['hcp'].append(dict(hcp_id=cid('hcp',i),display_name=f"Synthetic Professional {i:04}",speciality=['GENERAL','CARDIOLOGY','DERMATOLOGY'][i%3],country=config['country'],postal_sector=f"ZZ{i%20:03}",active=i!=97))
        world['affiliation'].append(dict(affiliation_id=f"AFF-{i:06}",hcp_id=cid('hcp',i),hco_id=cid('hco',(i-1)%12+1),relationship_type="PRACTISES_AT",is_primary=True,effective_from='2026-07-01',effective_to=''))
        if i not in config['defects']['missing_territory_hcps']:
            world['hcp_territory'].append(dict(assignment_id=f"ASSIGN-{i:06}",hcp_id=cid('hcp',i),territory_id=cid('territory',(i-1)%4+1),effective_from='2026-07-01',effective_to=''))
    # Deliberate overlapping intervals; the more recently effective assignment wins.
    world['hcp_territory'].append(dict(assignment_id="ASSIGN-REALIGN",hcp_id=cid('hcp',1),territory_id=cid('territory',2),effective_from='2026-09-01',effective_to=''))
    world['hcp_territory'].append(dict(assignment_id="ASSIGN-FUTURE",hcp_id=cid('hcp',2),territory_id=cid('territory',3),effective_from='2026-10-01',effective_to=''))
    for i in range(1,5):
        world['product'].append(dict(product_id=cid('product',i),product_name=f"Synthetic Product {i}",active=True))
        world['product_hierarchy'].append(dict(product_id=cid('product',i),effective_from='2026-07-01',effective_to='2026-09-15' if i==1 else '',brand=f"SYNTH_BRAND_{i}",therapy='SYNTH_THERAPY_A' if i<3 else 'SYNTH_THERAPY_B'))
        world['territory'].append(dict(territory_id=cid('territory',i),territory_name=f"Synthetic Territory {i}"))
    world['product_hierarchy'].append(dict(product_id=cid('product',1),effective_from='2026-09-15',effective_to='',brand='SYNTH_BRAND_1_REVISED',therapy='SYNTH_THERAPY_A'))
    for i in range(1,9):
        world['representative'].append(dict(rep_id=cid('representative',i),rep_name=f"Synthetic Rep {i}"))
        world['rep_territory'].append(dict(rep_id=cid('representative',i),territory_id=cid('territory',(i-1)%4+1),effective_from='2026-07-01',effective_to=''))
    decisions = {}
    def activity(i,h,p,dt,version=1,batch='b001',operation='UPSERT',approval='APPROVED',decision='ACCEPT',modified=None):
        world['interaction'].append(dict(interaction_id=cid('interaction',i),version_no=version,hcp_id=cid('hcp',h),rep_id=cid('representative',(i-1)%8+1),primary_product_id=cid('product',p),occurred_at=dt,channel='EMAIL',approval=approval,duration_minutes=10+i%21,modified_at=modified or dt,operation=operation,delivery_batch=batch))
        world['interaction_product'].append(dict(interaction_id=cid('interaction',i),version_no=version,product_id=cid('product',p),detail_rank=1))
        decisions[f"{cid('interaction',i)}|{version}"]=decision
    for i in range(1,count+1):
        dt=(date(2026,7,1)+timedelta(days=rng.randrange(75))).isoformat()+"T12:00:00Z"
        activity(i,(i-1)%n+1,(i-1)%4+1,dt,approval='DRAFT' if i%41==0 else 'APPROVED')
        if i%17==0:
            world['interaction_product'].append(dict(interaction_id=cid('interaction',i),version_no=1,product_id=cid('product',i%4+1),detail_rank=2))
    # Exact boundary dates for campaign qualification.
    world['interaction'][4]['occurred_at']='2026-08-01T00:00:00Z'
    world['interaction'][5]['occurred_at']='2026-09-01T00:00:00Z'
    for r in world['interaction'][4:6]:r['modified_at']=r['occurred_at']
    activity(1,1,2,world['interaction'][0]['occurred_at'],2,'b002',modified='2026-09-14T18:00:00Z')
    activity(2,2,2,world['interaction'][1]['occurred_at'],2,'b002','DELETE',modified='2026-09-14T18:30:00Z')
    activity(count+1,5,1,'2026-09-08T12:00:00Z',batch='b002')
    activity(count+2,6,2,'2026-09-07T12:00:00Z',batch='b002',decision='LATE_BEYOND_WINDOW')
    activity(count+3,7,3,'2026-09-14T12:00:00Z',batch='b002',decision='MISSING_REQUIRED')
    activity(count+4,8,4,'2026-09-14T12:00:00Z',batch='b002')
    for i in range(1,n+1):
        if i not in config['defects']['missing_consent_hcps']:
            world['consent_event'].append(dict(consent_id=f"CONSENT-{i:06}",hcp_id=cid('hcp',i),channel='EMAIL',purpose='COMMERCIAL',status='GRANTED',effective_at='2026-07-01T00:00:00Z',sequence_no=1,delivery_batch='b001'))
    for i in config['defects']['withdrawn_hcps']:
        world['consent_event'].append(dict(consent_id=f"WITHDRAW-{i}",hcp_id=cid('hcp',i),channel='EMAIL',purpose='COMMERCIAL',status='WITHDRAWN',effective_at='2026-09-14T15:00:00Z',sequence_no=2,delivery_batch='b002'))
    # Future preference must not hide the current withdrawal.
    world['consent_event'].append(dict(consent_id='FUTURE-3',hcp_id=cid('hcp',3),channel='EMAIL',purpose='COMMERCIAL',status='GRANTED',effective_at='2026-10-01T00:00:00Z',sequence_no=3,delivery_batch='b002'))
    for i in range(1,5):
        world['campaign'].append(dict(campaign_id=cid('campaign',i),product_id=cid('product',i),start_date='2026-08-01',end_date_exclusive='2026-09-01',status='CANCELLED' if i==4 else 'ACTIVE'))
        members=list(range(1,20))+[100] if i==1 else list(range(20*(i-1)+1,20*i+1))
        for h in members:
            world['campaign_member'].append(dict(membership_id=f"MEM-{i}-{h}",campaign_id=cid('campaign',i),hcp_id=cid('hcp',h),member_status='ENROLLED'))
    for h in range(1,n+1):
        for p in range(1,5):
            for week in range(10):
                trx=rng.randrange(1,40)
                world['rx_sales'].append(dict(observation_id=f"OBS-{h}-{p}-{week}",version_no=1,hcp_id=cid('hcp',h),product_id=cid('product',p),week_ending=(date(2026,7,5)+timedelta(days=7*week)).isoformat(),trx_count=trx,nrx_count=trx//3,sales_units=trx*2))
    # A concrete wholesale replacement/restatement, never an additive delta.
    restatement=copy.deepcopy(world['rx_sales'][0]);restatement.update(version_no=2,trx_count=50,nrx_count=10,sales_units=100)
    world['rx_sales'].append(restatement)

    source={b['id']:{} for b in config['batches']}
    def add(batch,name,row): source[batch].setdefault(name,[]).append(row)
    def idx(value): return int(value.rsplit('-',1)[1])
    for r in world['hcp']:
        i=idx(r['hcp_id'])
        add('b001','iqvia_like/provider',dict(provider_key=ident('hcp',i,'iqvia'),link_token=token('hcp',i),label=r['display_name'],speciality=r['speciality'],active=str(r['active']).lower(),country=r['country'],postal_sector=r['postal_sector']))
        add('b001','veeva_like/customer',dict(customer_key=ident('hcp',i,'veeva'),match_token='' if i in config['defects']['unmatched_crm_hcps'] else token('hcp',i),display_name=r['display_name'].upper(),active=str(r['active']).lower()))
        add('b001','salesforce_like/contact',dict(contact_key=ident('hcp',i,'salesforce'),match_token='' if i in config['defects']['unmatched_salesforce_hcps'] else token('hcp',i),display_name=r['display_name'].replace('Professional','Prof')))
    for r in world['hco']:
        add('b001','iqvia_like/organisation',dict(organisation_key=ident('hco',idx(r['hco_id']),'iqvia'),organisation_name=r['organisation_name'],country=r['country']))
    for r in world['affiliation']:
        add('b001','iqvia_like/affiliation',dict(affiliation_key=r['affiliation_id'],provider_key=ident('hcp',idx(r['hcp_id']),'iqvia'),organisation_key=ident('hco',idx(r['hco_id']),'iqvia'),relationship_type=r['relationship_type'],is_primary='true',effective_from=r['effective_from'],effective_to=r['effective_to']))
    for r in world['product_hierarchy']:
        add('b001','iqvia_like/product',dict(product_code=ident('product',idx(r['product_id']),'iqvia'),brand=r['brand'],therapy=r['therapy'],valid_from=r['effective_from'],valid_to=r['effective_to'],active='true'))
    for r in world['territory']:
        add('b001','veeva_like/territory',dict(territory_code=ident('territory',idx(r['territory_id']),'veeva'),territory_name=r['territory_name']))
    for r in world['representative']:
        add('b001','veeva_like/staff',dict(staff_key=ident('representative',idx(r['rep_id']),'veeva'),staff_name=r['rep_name']))
    for r in world['interaction']:
        i=idx(r['interaction_id']);v=r['version_no'];b=r['delivery_batch']
        badproduct=i in config['defects']['unknown_product_interactions']
        row=dict(activity_key=ident('interaction',i,'veeva'),customer_key=ident('hcp',idx(r['hcp_id']),'veeva'),primary_product_code='SYN_UNKNOWN_PRODUCT' if badproduct else ident('product',idx(r['primary_product_id']),'iqvia'),occurred_at='' if i==count+3 else r['occurred_at'],channel=r['channel'],approval=r['approval'],duration_minutes=r['duration_minutes'],source_version=v,modified_at=r['modified_at'],operation=r['operation'])
        add(b,'veeva_like/activity',row)
        if i==1 and v==1: add(b,'veeva_like/activity',copy.deepcopy(row))
        for detail in [d for d in world['interaction_product'] if d['interaction_id']==r['interaction_id'] and d['version_no']==v]:
            add(b,'veeva_like/activity_product',dict(activity_key=row['activity_key'],source_version=v,product_code='SYN_UNKNOWN_PRODUCT' if badproduct else ident('product',idx(detail['product_id']),'iqvia'),detail_rank=detail['detail_rank']))
    for r in world['consent_event']:
        add(r['delivery_batch'],'salesforce_like/consent',dict(preference_key=r['consent_id'],contact_key=ident('hcp',idx(r['hcp_id']),'salesforce'),channel=r['channel'],purpose=r['purpose'],status=r['status'],effective_at=r['effective_at'],sequence_no=r['sequence_no']))
    for r in world['campaign']:
        add('b001','salesforce_like/campaign',dict(campaign_key=ident('campaign',idx(r['campaign_id']),'salesforce'),product_code=ident('product',idx(r['product_id']),'iqvia'),start_date=r['start_date'],end_date_exclusive=r['end_date_exclusive'],status=r['status']))
    for r in world['campaign_member']:
        add('b001','salesforce_like/campaign_member',dict(membership_key=r['membership_id'],campaign_key=ident('campaign',idx(r['campaign_id']),'salesforce'),contact_key=ident('hcp',idx(r['hcp_id']),'salesforce'),member_status=r['member_status']))
    for r in world['hcp_territory']:
        add('b001','manual/territory_mapping',dict(assignment_key=r['assignment_id'],provider_key=ident('hcp',idx(r['hcp_id']),'iqvia'),territory_code=ident('territory',idx(r['territory_id']),'veeva'),effective_from=r['effective_from'],effective_to=r['effective_to']))
    for r in world['rx_sales']:
        add('b002' if r['version_no']==2 else 'b001','iqvia_like/rx_weekly',dict(observation_key=r['observation_id'],provider_key=ident('hcp',idx(r['hcp_id']),'iqvia'),product_code=ident('product',idx(r['product_id']),'iqvia'),week_ending=r['week_ending'],trx_count=r['trx_count'],nrx_count=r['nrx_count'],sales_units=r['sales_units'],version_no=r['version_no']))
    contracts={}
    for batch in config['batches']:
        files=[]
        for name,rows in sorted(source[batch['id']].items()):
            cols=list(rows[0]); key=f"synthetic/pharma/{config['release_id']}/sources/{name}/batch={batch['id']}/part-00001.csv"
            target=dest/'public_s3'/key
            write_csv(target,rows,cols)
            files.append(dict(key=key,source_entity=name,schema_version='1.0',columns=cols,row_count=len(rows),byte_count=target.stat().st_size,sha256=sha256(target),format='CSV',encoding='UTF-8',delimiter=',',header=True))
            key_columns={'veeva_like/activity':['activity_key','source_version'],
                         'veeva_like/activity_product':['activity_key','source_version','product_code'],
                         'iqvia_like/product':['product_code','valid_from'],
                         'iqvia_like/rx_weekly':['observation_key','version_no']}.get(name,[cols[0]])
            numeric={'source_version','version_no','duration_minutes','detail_rank','sequence_no','trx_count','nrx_count','sales_units'}
            dates={'effective_from','effective_to','valid_from','valid_to','start_date','end_date_exclusive','week_ending'}
            logical={c:('INTEGER' if c in numeric else 'DATE' if c in dates else 'TIMESTAMP_UTC' if c.endswith('_at') else 'BOOLEAN' if c in {'active','is_primary'} else 'TEXT') for c in cols}
            contracts[name]=dict(columns=cols,logical_types=logical,schema_version='1.0',format='CSV',null_representation='empty field',key_columns=key_columns,delivery='versioned append' if name in ['veeva_like/activity','veeva_like/activity_product','iqvia_like/rx_weekly'] else 'initial snapshot plus explicit event/interval history')
        manifest=dict(manifest_version='1.0',release_id=config['release_id'],batch_id=batch['id'],available_at=batch['available_at'],as_of=batch['as_of'],load_mode=batch['mode'],files=files)
        manifest_path=dest/'public_s3'/f"synthetic/pharma/{config['release_id']}/control/{batch['id']}.manifest.json"
        write_json(manifest_path,manifest)
        write_json(manifest_path.with_name(f"{batch['id']}.ready.json"),dict(batch_id=batch['id'],manifest_sha256=sha256(manifest_path)))
    for name,rows in world.items():
        write_csv(dest/'private_evaluator/canonical'/f'{name}.csv', rows,[c['name'] for c in definitions()[name]['columns']])
    write_json(dest/'private_evaluator/canonical-manifest.json',{
        'manifest_version':'1.0','release_id':config['release_id'],'classification':'EVALUATOR_ONLY',
        'files':[{'entity':name,'path':f'canonical/{name}.csv','row_count':len(rows),
                  'sha256':sha256(dest/'private_evaluator/canonical'/f'{name}.csv'),
                  'columns':[c['name'] for c in definitions()[name]['columns']]} for name,rows in world.items()]})
    write_json(dest/'private_evaluator/world.json',world)
    write_json(dest/'private_evaluator/projection-ledger.json',dict(decisions=decisions,config=config))
    write_json(dest/'public_s3'/f"synthetic/pharma/{config['release_id']}/control/source-contracts.json",contracts)
    write_json(dest/'generator-input.json',config)
    return world

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=ROOT/'config/crawl.json');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    export();world=generate(read_json(a.config),a.out)
    print('Generated',sum(map(len,world.values())),'canonical rows into',a.out)
