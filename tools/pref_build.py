# 県ごとの市町村データ（読みがな・人口・年齢構成・面積・人口密度）を作るスクリプト。政令指定都市は区単位
# 使い方: python pref_build.py <このフォルダ> <住基xlsx> <面積pdf> <県コード2桁> <出力json>
#   住基xlsx: 総務省「住民基本台帳に基づく人口、人口動態及び世帯数」年齢階級別人口（市区町村別）（総計）
#   面積pdf : 国土地理院「全国都道府県市区町村別面積調」
# 必要なライブラリ: pypdf（Excelは xlsx.py で標準機能だけで読む）
import re,sys,json
sys.path.insert(0,sys.argv[1])
from xlsx import read
import pypdf
natl,pdf,pc,out=sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5]
rows,_=read(natl)
pop={}
for r in rows:
    if len(r)>25 and r[0] and str(r[0]).startswith(pc) and r[2] not in (None,'-') and r[3]=='計':
        v=[int(x) for x in r[4:26]]
        pop[str(r[0])[:5]]={'name':r[2],'p':v[0],'y':sum(v[1:4]),'e65':sum(v[14:]),'e75':sum(v[16:])}
# 県の見出し（例: '４０　福 岡 県'）で始まるページだけを使う
fw=pc.translate(str.maketrans('0123456789','０１２３４５６７８９'))+'　'
seg=chr(10).join(t for t in ((p.extract_text() or '') for p in pypdf.PdfReader(pdf).pages) if t.startswith(fw))
area={}
for m in re.finditer(r'(\d{3}) (?:(\S+) )?([ぁ-ゖ]+) (?:\* )?([\d,]+\.\d+)',seg):
    area.setdefault(pc+m.group(1),(float(m.group(4).replace(',','')),m.group(3)))   # (面積, 読みがな)
D=[]
# 政令指定都市は区単位にする（市の合計行は使わない）。区のコードは下3桁が101〜199、市のコードは区の下1桁を0にしたもの
is_ward=lambda c: 100<int(c[2:5])<200 and c[4]!='0'
designated={c[:4]+'0' for c in pop if is_ward(c)}
for code,d in pop.items():
    if code in designated or d['name'].endswith('郡'): continue
    name=re.sub(r'^.+?郡(?=.+[町村]$)','',d['name'])
    name=name.replace('須惠町','須恵町')
    if code not in area: print('NO AREA',code,name.encode('utf-8'));continue
    a,kana=area[code]
    if is_ward(code): kana=area[code[:4]+'0'][1]+kana   # 読みは「市＋区」（例：ふくおかしちゅうおうく）
    D.append({'code':code,'name':name,'kana':kana,'population':d['p'],'young_pct':round(d['y']/d['p']*100,2),
      'work_pct':round((d['p']-d['y']-d['e65'])/d['p']*100,2),'elder_pct':round(d['e65']/d['p']*100,2),
      'age75_pct':round(d['e75']/d['p']*100,2),'age75_of65_pct':round(d['e75']/d['e65']*100,2),'area_km2':a,'density':round(d['p']/a,2)})
json.dump(D,open(out,'w',encoding='utf-8'),ensure_ascii=False)
print(len(D))
