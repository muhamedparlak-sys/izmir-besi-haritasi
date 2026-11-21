import requests
U="https://tucbs-public-api.csb.gov.tr/csb_cdp_im_wms"; H={"User-Agent":"Mozilla/5.0"}
for L in ["2","5","6","7","9"]:
    p=dict(SERVICE="WMS",REQUEST="GetMap",VERSION="1.3.0",LAYERS=L,STYLES="",CRS="EPSG:4326",BBOX="37.8,26.6,38.6,27.6",WIDTH=1000,HEIGHT=800,FORMAT="image/png",TRANSPARENT="TRUE")
    r=requests.get(U,params=p,headers=H,timeout=120); open(f"test_L{L}.png","wb").write(r.content); print(L,r.status_code,r.headers.get('content-type'),len(r.content))
