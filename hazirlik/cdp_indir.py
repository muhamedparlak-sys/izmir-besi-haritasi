import requests, os, time
U="https://tucbs-public-api.csb.gov.tr/csb_cdp_im_wms"; H={"User-Agent":"Mozilla/5.0"}
W,S,E,N=26.15,37.70,28.55,39.45
NX,NY=4,4; px=1200; py=int(px*(N-S)/(E-W)*NX/NY)
dx=(E-W)/NX; dy=(N-S)/NY
for L in ["2","5","7","9"]:
  for i in range(NX):
    for j in range(NY):
      f=f"ham/cdp/L{L}_{i}_{j}.png"
      if os.path.exists(f): continue
      w=W+i*dx; s=S+j*dy
      p=dict(SERVICE="WMS",REQUEST="GetMap",VERSION="1.3.0",LAYERS=L,STYLES="",CRS="EPSG:4326",
             BBOX=f"{s},{w},{s+dy},{w+dx}",WIDTH=px,HEIGHT=py,FORMAT="image/png",TRANSPARENT="TRUE")
      for k in range(4):
        try:
          r=requests.get(U,params=p,headers=H,timeout=180)
          if r.ok and r.headers.get('content-type','').startswith('image'): open(f,"wb").write(r.content); break
        except Exception as e: print("retry",f,e)
        time.sleep(3)
  print("katman",L,"tamam",flush=True)
print("px",px,py)
