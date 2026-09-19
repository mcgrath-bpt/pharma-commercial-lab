import copy
import csv
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT, read_json, write_json, write_results, read_csv, sha256
from generate import generate
from model import definitions
from oracle import expected
from reference import load_sources, calculate, rate_status, latest_territory
from validate import validate_public, reconcile
from xlsx_to_csv import convert
from upload_public import upload
import zipfile
import xml.etree.ElementTree as ET

class LabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.base=Path(cls.tmp.name);cls.path=cls.base/'a'
        cls.cfg=read_json(ROOT/'config/crawl.json');cls.world=generate(cls.cfg,cls.path)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def sources(self,batch='b002'):return load_sources(self.path/'public_s3',batch)
    def test_all_five_scenarios_and_diagnostics_both_checkpoints(self):
        for batch in ['b001','b002']:
            with self.subTest(batch=batch):
                t,cut=self.sources(batch);e=self.base/'expected'/batch;a=self.base/'actual'/batch
                write_results(e,expected(self.path/'private_evaluator',batch));write_results(a,calculate(t,cut))
                self.assertTrue(reconcile(e,a)['passed'])
    def test_manifest_bytes_schema_counts(self):
        self.assertEqual(validate_public(self.path/'public_s3')['batches'],2)
    def test_determinism(self):
        other=self.base/'determinism';generate(self.cfg,other)
        first={str(p.relative_to(self.path)):sha256(p) for p in self.path.rglob('*') if p.is_file()}
        second={str(p.relative_to(other)):sha256(p) for p in other.rglob('*') if p.is_file()}
        self.assertEqual(first,second)
    def test_canonical_keys_types_references_and_intervals(self):
        w=self.world
        for name,spec in definitions().items():
            rows=w[name];keys=[tuple(r[k] for k in spec['primary_key']) for r in rows]
            self.assertEqual(len(keys),len(set(keys)),name)
            for row in rows:
                for col in spec['columns']:
                    value=row[col['name']]
                    if value=='':self.assertTrue(col['nullable'],(name,col['name']))
                    elif col['type']=='DATE':datetime.strptime(value,'%Y-%m-%d')
                    elif col['type']=='TIMESTAMP_NTZ':datetime.fromisoformat(value.replace('Z','+00:00'))
                    elif col['type']=='NUMBER':self.assertIsInstance(value,int)
                    elif col['type']=='BOOLEAN':self.assertIsInstance(value,bool)
                if 'effective_from' in row and row.get('effective_to'):self.assertLess(row['effective_from'],row['effective_to'])
            for col,ref in spec['foreign_keys'].items():
                target,field=ref.split('.');allowed={r[field] for r in w[target]}
                self.assertTrue(all(r[col] in allowed for r in rows),(name,col))
        parents={(r['interaction_id'],r['version_no']) for r in w['interaction']}
        self.assertTrue(all((r['interaction_id'],r['version_no']) in parents for r in w['interaction_product']))
        for row in w['source_identity']:
            name=row['entity_type'];key=definitions()[name]['primary_key'][0]
            self.assertIn(row['canonical_id'],{r[key] for r in w[name]})
        self.assertTrue(all(r['nrx_count']<=r['trx_count'] for r in w['rx_sales']))
    def test_exact_thresholds_empty_and_over_boundary(self):
        for percent in [1,2,5]:
            self.assertEqual(rate_status(percent,100,percent),'PASS')
            self.assertEqual(rate_status(percent+1,100,percent),'ALERT')
            self.assertEqual(rate_status(0,0,percent),'NO_DATA')
    def test_replay_and_reordered_input(self):
        t,cut=self.sources();a=calculate(t,cut)
        replay={k:list(reversed(v+v)) for k,v in t.items()}
        b=calculate(replay,cut)
        # Reference source snapshots are intentionally unique; exact duplicate records allowed.
        for name in a:
            norm=lambda rows:sorted(tuple(sorted(r.items())) for r in rows)
            self.assertEqual(norm(a[name]),norm(b[name]),name)
    def test_later_deliveries_are_invisible_to_earlier_cutoff(self):
        earlier,cut=self.sources('b001');later,_=self.sources('b002')
        expected_result=calculate(earlier,cut);actual=calculate(later,cut)
        for name in expected_result:
            normal=lambda rows:sorted(tuple(sorted(r.items())) for r in rows)
            self.assertEqual(normal(expected_result[name]),normal(actual[name]),name)
    def test_equal_effective_territory_conflict_and_half_open_end(self):
        row=dict(effective_from='2026-09-01',effective_to='2026-09-15',territory_code='T1')
        self.assertEqual(latest_territory([row],'2026-09-15'),('','MISSING'))
        conflict=[dict(row,effective_to='',territory_code=t) for t in ['T1','T2']]
        with self.assertRaisesRegex(ValueError,'DUPLICATE_CURRENT'):latest_territory(conflict,'2026-09-15')
    def test_conflicting_same_version_fails(self):
        t,cut=self.sources();r=copy.deepcopy(t['veeva_like/activity'][0]);r['duration_minutes']='999';t['veeva_like/activity'].append(r)
        with self.assertRaisesRegex(ValueError,'CONFLICTING_INTERACTION'):calculate(t,cut)
    def test_hand_checked_incremental_cases(self):
        t,cut=self.sources();out=calculate(t,cut);ids={(r['canonical_id'],r['source']):r['source_id'] for r in self.world['source_identity']}
        ak=lambda i:ids[(f'INTERACTION-{i:06}','veeva')]
        rows={r['activity_key']:r for r in out['s04_interaction']}
        self.assertEqual(rows[ak(1)]['source_version'],'2')
        self.assertNotIn(ak(2),rows)
        self.assertIn(ak(301),rows)  # exactly seven calendar days late
        self.assertNotIn(ak(302),rows)  # eight days late
        self.assertNotIn(ak(303),rows)  # missing occurred_at
        self.assertEqual(len(rows),301)
        self.assertFalse(any(r['customer_key']==ids[('HCP-000003','iqvia')] for r in out['s01_engagement']))
        self.assertTrue(any(r['brand']=='SYNTH_BRAND_1_REVISED' for r in out['s02_product_activity']))
        self.assertEqual(len(out['s03_customer_territory']),99)
        self.assertEqual(sum(r['assignment_status']=='MISSING' for r in out['s03_customer_territory']),1)
        self.assertEqual(len(out['s05_campaign']),59)
        self.assertEqual(sum(r['qualifying_interactions']==0 for r in out['s05_campaign'])>0,True)
    def test_bad_bytes_are_rejected(self):
        bad=self.base/'badbytes';generate(self.cfg,bad);f=next((bad/'public_s3').rglob('*.csv'));f.write_bytes(f.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'fingerprint'):validate_public(bad/'public_s3')
    def test_reconciliation_detects_missing_duplicate_and_wrong_values(self):
        t,cut=self.sources();out=calculate(t,cut);a=self.base/'mutate/a';e=self.base/'mutate/e';write_results(e,out)
        for change in ['duplicate','missing','attribute']:
            x=copy.deepcopy(out)
            if change=='duplicate':x['s04_interaction'].append(x['s04_interaction'][0])
            elif change=='missing':x['s04_interaction'].pop()
            else:x['s04_interaction'][0]['duration_minutes']='999'
            write_results(a,x);self.assertFalse(reconcile(e,a)['passed'])
    def test_ambiguous_identity_is_not_arbitrarily_selected(self):
        t,cut=self.sources();r=copy.deepcopy(t['iqvia_like/provider'][0]);r['provider_key']='AMBIGUOUS';t['iqvia_like/provider'].append(r)
        out=calculate(t,cut);original=t['iqvia_like/provider'][0]['provider_key']
        self.assertFalse(any(r['customer_key']==original for r in out['s01_engagement']))
    def test_xlsx_roundtrip_and_formula_rejection(self):
        source=ROOT/'data/public_s3/synthetic/pharma/pharma-lab-0.1.0/business_files/territory/territory_mapping_202609.xlsx'
        if not source.exists():self.skipTest('Static workbook is not present')
        csvout=self.base/'adapted.csv';receipt=convert(source,csvout)
        original=next((self.path/'public_s3').rglob('territory_mapping/batch=b001/part-00001.csv'))
        self.assertEqual(csvout.read_bytes(),original.read_bytes());self.assertEqual(receipt['row_count'],101)
        bad=self.base/'formula.xlsx'
        with zipfile.ZipFile(source) as z,zipfile.ZipFile(bad,'w') as target:
            for name in z.namelist():
                content=z.read(name)
                if name=='xl/worksheets/sheet1.xml':
                    xml=ET.fromstring(content);ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
                    cell=next(xml.iter('{'+ns+'}c'));ET.SubElement(cell,'{'+ns+'}f').text='1+1';content=ET.tostring(xml)
                target.writestr(name,content)
        with self.assertRaisesRegex(ValueError,'Formula'):convert(bad,self.base/'bad.csv')
    def test_schema_drift_and_missing_file_fail_even_with_new_hash(self):
        bad=self.base/'drift';generate(self.cfg,bad)
        public=bad/'public_s3';mp=next(public.rglob('b001.manifest.json'));m=read_json(mp);f=m['files'][0];file=public/f['key']
        lines=file.read_text().splitlines();headers=lines[0].split(',');headers[0]='unexpected_column';lines[0]=','.join(headers);file.write_text('\n'.join(lines)+'\n')
        f['sha256']=sha256(file);f['byte_count']=file.stat().st_size;write_json(mp,m);write_json(mp.with_name('b001.ready.json'),dict(batch_id='b001',manifest_sha256=sha256(mp)))
        with self.assertRaisesRegex(ValueError,'Header'):validate_public(public)
        file.rename(file.with_suffix('.missing'))
        with self.assertRaises(FileNotFoundError):validate_public(public)
    def test_uploader_refuses_unlisted_private_material(self):
        bad=self.base/'leak';generate(self.cfg,bad)
        (bad/'public_s3/world.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Unlisted'):upload(bad/'public_s3','s3://example-only/',False)

if __name__=='__main__':unittest.main(verbosity=2)
