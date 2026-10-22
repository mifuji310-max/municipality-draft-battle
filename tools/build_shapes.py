# 市町村の形データを作るスクリプト
# 使い方: python build_shapes.py N03-21_40_210101.json shapes.json
# 入力: https://github.com/smartnews-smri/japan-topography の data/municipality/geojson/s0010/N03-21_40_210101.json
# 出典: 国土数値情報（行政区域データ）（国土交通省）
import json,sys,math,collections
src,out=sys.argv[1],sys.argv[2]
g=json.load(open(src,encoding='utf-8'))
LAT0=33.6;KX=math.cos(math.radians(LAT0))
def proj(p): return (round(p[0]*KX,6), round(-p[1],6))
def area(r):
  s=0
  for i in range(len(r)-1): s+=r[i][0]*r[i+1][1]-r[i+1][0]*r[i][1]
  return s/2
def centroid(r):
  a=area(r);cx=cy=0
  for i in range(len(r)-1):
    f=r[i][0]*r[i+1][1]-r[i+1][0]*r[i][1];cx+=(r[i][0]+r[i+1][0])*f;cy+=(r[i][1]+r[i+1][1])*f
  return (cx/(6*a),cy/(6*a))
groups=collections.defaultdict(list)
for f in g['features']:
  code=f['properties']['N03_007']
  if code.startswith('4010'): code='40100'
  if code.startswith('4013'): code='40130'
  geom=f['geometry'];polys=geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
  for poly in polys: groups[code].append([proj(p) for p in poly[0]])  # 外周のみ
def dissolve(rings):
  if len(rings)==1: return rings
  cnt=collections.Counter()
  for r in rings:
    for i in range(len(r)-1):
      a,b=r[i],r[i+1]
      if a!=b: cnt[frozenset((a,b))]+=1
  nxt={}
  for r in rings:
    for i in range(len(r)-1):
      a,b=r[i],r[i+1]
      if a!=b and cnt[frozenset((a,b))]==1: nxt.setdefault(a,[]).append(b)
  res=[];used=set()
  for s in list(nxt):
    while nxt.get(s):
      ring=[s];cur=s
      while True:
        b=nxt[cur].pop();cur=b;ring.append(b)
        if b==s or not nxt.get(b): break
      if len(ring)>3: res.append(ring)
  return res
def rdp(pts,eps):
  if len(pts)<3: return pts
  a,b=pts[0],pts[-1];dx,dy=b[0]-a[0],b[1]-a[1];L=math.hypot(dx,dy) or 1e-12
  dmax,idx=0,0
  for i in range(1,len(pts)-1):
    d=abs(dy*pts[i][0]-dx*pts[i][1]+b[0]*a[1]-b[1]*a[0])/L if (dx or dy) else math.hypot(pts[i][0]-a[0],pts[i][1]-a[1])
    if d>dmax: dmax,idx=d,i
  if dmax>eps: return rdp(pts[:idx+1],eps)[:-1]+rdp(pts[idx:],eps)
  return [a,b]
def inside(pt,r):
  x,y=pt;c=False
  for i in range(len(r)-1):
    (x1,y1),(x2,y2)=r[i],r[i+1]
    if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1: c=not c
  return c
def segdist(p,a,b):
  dx,dy=b[0]-a[0],b[1]-a[1];l=dx*dx+dy*dy
  t=0 if l==0 else max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/l))
  return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
report=[];shapes={}
for code,rings in sorted(groups.items()):
  rings=dissolve(rings)
  rings=sorted(rings,key=lambda r:-abs(area(r)))
  main=rings[0];ma=abs(area(main));mc=centroid(main)
  mr=max(math.hypot(p[0]-mc[0],p[1]-mc[1]) for p in main)
  keep=[main];info=[]
  for r in rings[1:]:
    a=abs(area(r));c=centroid(r);d=math.hypot(c[0]-mc[0],c[1]-mc[1])
    info.append((round(a/ma*100,2),round(d/mr,2)))
    if a/ma<0.002: continue
    if d>2.2*mr:  # 遠い島は本土の近くへ寄せて表示（はめ込み）
      k=(2.0*mr)/d;ox=mc[0]+(c[0]-mc[0])*k-c[0];oy=mc[1]+(c[1]-mc[1])*k-c[1]
      r=[(p[0]+ox,p[1]+oy) for p in r]
    keep.append(r)
  allp=[p for r in keep for p in r]
  minx=min(p[0] for p in allp);maxx=max(p[0] for p in allp);miny=min(p[1] for p in allp);maxy=max(p[1] for p in allp)
  cx,cy=(minx+maxx)/2,(miny+maxy)/2;half=max(maxx-minx,maxy-miny)/2
  norm=lambda p:((p[0]-cx)/half*100,(p[1]-cy)/half*100)
  outr=[]
  for r in keep:
    q=rdp([norm(p) for p in r],0.6)
    q=[(round(x),round(y)) for x,y in q]
    dedup=[q[0]]
    for p in q[1:]:
      if p!=dedup[-1]: dedup.append(p)
    if len(dedup)>=4: outr.append(dedup)
  # 目の位置：本土の中で縁から最も遠い点（簡易グリッド探索）
  m=outr[0];best=(0,(0,0))
  for gx in range(-100,101,4):
    for gy in range(-100,101,4):
      if inside((gx,gy),m):
        d=min(segdist((gx,gy),m[i],m[i+1]) for i in range(len(m)-1))
        if d>best[0]: best=(d,(gx,gy))
  shapes[code]={'r':[[c for p in r[:-1] for c in p] for r in outr],'e':list(best[1]),'ei':round(best[0])}
  report.append((code,len(rings),len(outr),sum(len(r) for r in outr),info,best))
for row in report: print(row)
json.dump(shapes,open(out,'w',encoding='utf-8'),separators=(',',':'))
