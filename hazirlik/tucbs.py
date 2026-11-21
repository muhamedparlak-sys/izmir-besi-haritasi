import requests, json, sys
U="https://tucbs-public-api.csb.gov.tr/csb_cdp_im_wms"
H={"User-Agent":"Mozilla/5.0"}
def fi(lat,lng,layers="2,3,4,5,6,7,9,11,12,17",fmt="application/geojson"):
    d=0.002
    p=dict(SERVICE="WMS",REQUEST="GetFeatureInfo",VERSION="1.3.0",LAYERS=layers,QUERY_LAYERS=layers,
           INFO_FORMAT=fmt,WIDTH=101,HEIGHT=101,CRS="EPSG:4326",
           BBOX=f"{lat-d},{lng-d},{lat+d},{lng+d}",I=50,J=50,FEATURE_COUNT=20,STYLES="")
    r=requests.get(U,params=p,headers=H,timeout=40); return r
if __name__=="__main__":
    for lat,lng in [(38.10,27.85),(39.10,27.20),(38.62,27.05),(38.25,27.15)]:
        r=fi(lat,lng); print("==",lat,lng,r.status_code,len(r.content)); print(r.text[:1500])
