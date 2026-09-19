"""Evaluator only: canonical truth plus explicit projection decisions.

Does not import the source reference or read rendered source files. The explicit
ACCEPT/LATE/MISSING ledger makes delivery-policy expectations independent of the
implementation under test. It is an oracle for this fixture, not market truth.
"""
import argparse
from collections import defaultdict
from pathlib import Path
from common import read_json, write_results

def expected(private_root,batch):
    w=read_json(private_root/'world.json');ledger=read_json(private_root/'projection-ledger.json');cfg=ledger['config']
    as_of=next(b['as_of'] for b in cfg['batches'] if b['id']==batch);day=as_of[:10]
    ids={(r['entity_type'],r['canonical_id'],r['source']):r['source_id'] for r in w['source_identity']}
    def sid(kind,value,source):return ids[(kind,value,source)]
    def ix(cid):return int(cid.rsplit('-',1)[1])
    def hkey(h):return sid('hcp',h,'iqvia')
    live={r['hcp_id'] for r in w['hcp'] if r['active']}
    def crm_ok(h):return h in live and ix(h) not in cfg['defects']['unmatched_crm_hcps']
    def sf_ok(h):return h in live and ix(h) not in cfg['defects']['unmatched_salesforce_hcps']
    out=defaultdict(list)
    def issue(s,k,r):out['exceptions'].append(dict(scenario=s,record_key=k,reason=r))
    def dq(s,k,n,d,limit):
        state='NO_DATA' if d==0 else ('ALERT' if n/d>limit else 'PASS')
        out['dq'].append(dict(scenario=s,scope=k,numerator=n,denominator=d,threshold=limit,status=state))
    selected={}
    for event in w['interaction']:
        if event['delivery_batch']>batch:continue
        cid=event['interaction_id'];decision=ledger['decisions'][cid+'|'+str(event['version_no'])]
        if decision!='ACCEPT':issue('S04',sid('interaction',cid,'veeva'),decision);continue
        if cid not in selected or event['version_no']>selected[cid]['version_no']:selected[cid]=event
    selected={k:r for k,r in selected.items() if r['operation']!='DELETE'}
    def pkey(p):return sid('product',p,'iqvia')
    def products(r):
        if ix(r['interaction_id']) in cfg['defects']['unknown_product_interactions']:return set()
        return {x['product_id'] for x in w['interaction_product'] if x['interaction_id']==r['interaction_id'] and x['version_no']==r['version_no']}
    for cid,r in selected.items():
        p='SYN_UNKNOWN_PRODUCT' if ix(cid) in cfg['defects']['unknown_product_interactions'] else pkey(r['primary_product_id'])
        out['s04_interaction'].append(dict(activity_key=sid('interaction',cid,'veeva'),customer_key=sid('hcp',r['hcp_id'],'veeva'),primary_product_code=p,occurred_at=r['occurred_at'],channel=r['channel'],duration_minutes=r['duration_minutes'],source_version=r['version_no']))
    approved=[r for r in selected.values() if r['approval']=='APPROVED']
    dq('S01','ALL',sum(not crm_ok(r['hcp_id']) for r in approved),len(approved),0.02)
    dq('S02','ALL',sum(not products(r) for r in approved),len(approved),0.01)
    totals=defaultdict(set)
    for r in approved:
        h=r['hcp_id'];aid=sid('interaction',r['interaction_id'],'veeva');date=r['occurred_at'][:10]
        if not crm_ok(h):issue('S01',aid,'UNMATCHED_CUSTOMER')
        else:
            events=[c for c in w['consent_event'] if c['hcp_id']==h and sf_ok(h) and c['delivery_batch']<=batch and c['effective_at']<=as_of and c['channel']==r['channel'] and c['purpose']=='COMMERCIAL']
            if not events:issue('S01',aid,'MISSING_CONSENT')
            else:
                latest=sorted(events,key=lambda e:(e['effective_at'],e['sequence_no']))[-1]
                if latest['status']!='GRANTED':issue('S01',aid,'WITHDRAWN_OR_UNKNOWN_CONSENT')
                else:out['s01_engagement'].append(dict(activity_key=aid,customer_key=hkey(h),activity_date=date,consent_status='GRANTED'))
        ps=products(r)
        if not ps:issue('S02',aid,'UNKNOWN_PRODUCT')
        if not crm_ok(h):issue('S02',aid,'UNMATCHED_CUSTOMER')
        else:
            for p in ps:totals[(h,p,date)].add(aid)
    for (h,p,date),hits in totals.items():
        hierarchy=next(x for x in w['product_hierarchy'] if x['product_id']==p and x['effective_from']<=day and (not x['effective_to'] or day<x['effective_to']))
        out['s02_product_activity'].append(dict(customer_key=hkey(h),product_code=pkey(p),activity_date=date,brand=hierarchy['brand'],therapy=hierarchy['therapy'],interaction_count=len(hits)))
    for h in sorted(live):
        assignments=[x for x in w['hcp_territory'] if x['hcp_id']==h and x['effective_from']<=day and (not x['effective_to'] or day<x['effective_to'])]
        code=sid('territory',max(assignments,key=lambda x:x['effective_from'])['territory_id'],'veeva') if assignments else ''
        out['s03_customer_territory'].append(dict(customer_key=hkey(h),territory_code=code,assignment_status='ASSIGNED' if code else 'MISSING'))
        if not code:issue('S03',hkey(h),'MISSING_TERRITORY')
    for c in w['campaign']:
        if c['status']=='CANCELLED':continue
        cid=sid('campaign',c['campaign_id'],'salesforce');members=[m for m in w['campaign_member'] if m['campaign_id']==c['campaign_id'] and m['member_status']=='ENROLLED']
        dq('S05',cid,sum(not sf_ok(m['hcp_id']) for m in members),len(members),0.05)
        for m in members:
            h=m['hcp_id']
            if not sf_ok(h):issue('S05',cid+'|'+sid('hcp',h,'salesforce'),'UNMATCHED_MEMBER');continue
            hits=set()
            for r in approved:
                if r['hcp_id']==h and crm_ok(h) and c['start_date']<=r['occurred_at'][:10]<c['end_date_exclusive'] and c['product_id'] in products(r):hits.add(r['interaction_id'])
            out['s05_campaign'].append(dict(campaign_key=cid,customer_key=hkey(h),product_code=pkey(c['product_id']),contacted=str(len(hits)>0).lower(),qualifying_interactions=len(hits)))
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);p.add_argument('--batch',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    write_results(a.out,expected(a.private_root,a.batch));print('Independent canonical oracle complete:',a.batch)
