"""Narrow XLSX territory adapter, Python standard library only.

Accepts one named sheet, exact headers, text IDs and Excel/ISO dates. Rejects
formulas, merged cells and unexpected columns. Deliberately not a generic Excel
ingestion engine. Output is canonical UTF-8 CSV plus a provenance receipt.
"""
import argparse
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path
from common import write_csv, write_json, sha256

COLS=['assignment_key','provider_key','territory_code','effective_from','effective_to']
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

def convert(source,target):
    with zipfile.ZipFile(source) as z:
        book=ET.fromstring(z.read('xl/workbook.xml'))
        properties=book.find('s:workbookPr',NS)
        if properties is not None and properties.get('date1904') in ('1','true'):raise ValueError('1904 date system unsupported')
        sheet=next((x for x in book.findall('s:sheets/s:sheet',NS) if x.get('name')=='Territory'),None)
        if sheet is None:raise ValueError('Required sheet Territory is absent')
        relationships=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        relid=sheet.get('{'+NS['r']+'}id')
        part=next(r.get('Target') for r in relationships if r.get('Id')==relid)
        part=part.lstrip('/') if part.startswith('/') else posixpath.normpath('xl/'+part)
        xml=ET.fromstring(z.read(part))
        if xml.find('s:mergeCells',NS) is not None:raise ValueError('Merged cells unsupported')
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(t.text or '' for t in si.iter('{'+NS['s']+'}t')) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rows=[]
        for row in xml.findall('s:sheetData/s:row',NS):
            values=['']*5
            for cell in row.findall('s:c',NS):
                if cell.find('s:f',NS) is not None:raise ValueError('Formula cells are not accepted')
                letter=re.match(r'[A-Z]+',cell.get('r')).group();col=0
                for c in letter:col=col*26+ord(c)-64
                if col>5:raise ValueError('Unexpected column')
                v=cell.find('s:v',NS);raw=v.text if v is not None and v.text else '';kind=cell.get('t','n')
                if kind=='s':value=strings[int(raw)]
                elif kind=='inlineStr':value=''.join(x.text or '' for x in cell.findall('.//s:t',NS))
                elif int(row.get('r'))>1 and col in (4,5) and raw:
                    if kind=='n':
                        serial=float(raw)
                        if not serial.is_integer():raise ValueError('Dates must not contain time fractions')
                        value=(date(1899,12,30)+timedelta(days=int(serial))).isoformat()
                    else:value=raw[:10]
                else:value=raw
                values[col-1]=value
            rows.append(values)
    if not rows or rows[0]!=COLS:raise ValueError('Header contract mismatch')
    records=[dict(zip(COLS,row)) for row in rows[1:]]
    for r in records:
        if not all(r[k] for k in COLS[:4]):raise ValueError('Missing required mapping field')
        for k in COLS[3:]:
            if r[k]:date.fromisoformat(r[k])
        if r['effective_to'] and r['effective_to']<=r['effective_from']:raise ValueError('Invalid date interval')
    write_csv(target,records,COLS)
    receipt=dict(adapter_version='1.0',sheet='Territory',input_sha256=sha256(source),output_sha256=sha256(target),row_count=len(records),columns=COLS)
    write_json(Path(str(target)+'.receipt.json'),receipt)
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('target',type=Path);a=p.parse_args();print(convert(a.source,a.target))
