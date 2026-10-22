# 外部ライブラリなしで .xlsx の1シートを読む簡易リーダー
import zipfile,re,sys,xml.etree.ElementTree as ET
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def col(ref):
    s=re.match(r'[A-Z]+',ref).group();n=0
    for ch in s:n=n*26+ord(ch)-64
    return n-1
def read(path,sheet_index=0):
    z=zipfile.ZipFile(path)
    ss=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',NS):
            ss.append(''.join(t.text or '' for t in si.iter('{%s}t'%NS['m'])))
    sheets=sorted([n for n in z.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml',n)],key=lambda n:int(re.findall(r'\d+',n)[-1]))
    root=ET.fromstring(z.read(sheets[sheet_index]))
    rows=[]
    for r in root.iter('{%s}row'%NS['m']):
        row={}
        for c in r.findall('m:c',NS):
            v=c.find('m:v',NS);t=c.get('t')
            if v is None:
                isv=c.find('m:is',NS)
                val=''.join(x.text or '' for x in isv.iter('{%s}t'%NS['m'])) if isv is not None else None
            else:
                val=ss[int(v.text)] if t=='s' else v.text
            row[col(c.get('r'))]=val
        rows.append([row.get(i) for i in range(max(row)+1)] if row else [])
    return rows,len(sheets)
if __name__=='__main__':
    rows,n=read(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 0)
    out=['sheets=%d rows=%d'%(n,len(rows))]
    for r in rows[:int(sys.argv[3]) if len(sys.argv)>3 else 12]: out.append(' | '.join('' if x is None else str(x) for x in r))
    sys.stdout.buffer.write('\n'.join(out).encode('utf-8'))
