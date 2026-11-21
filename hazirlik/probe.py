import json
from tucbs import fi
pts={"Tire ova":(38.12,27.70),"Ödemiş ova":(38.20,27.95),"Bergama ova":(39.08,27.10),"Menemen ova":(38.60,27.02),"Torbalı":(38.15,27.38),"Kınık":(39.08,27.38)}
for n,(la,lo) in pts.items():
    print("==",n)
    for L in ["3","4","5","6","7","9","11","12","17"]:
        r=fi(la,lo,layers=L)
        t=r.content.decode('utf-8',errors='ignore')
        try: d=json.loads(r.content.decode('cp1254'))
        except Exception as e:
            try: d=json.loads(r.content.decode('utf-8'))
            except: print(L,"parse fail",t[:100]); continue
        for f in d.get('features',[]):
            p={k:v for k,v in f['properties'].items() if v not in ('Null','') and not k.upper().startswith(('SHAPE','OBJECTID'))}
            print(" L",L,p)
