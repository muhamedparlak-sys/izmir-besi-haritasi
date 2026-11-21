import requests, os
os.makedirs("ham/dem",exist_ok=True)
for la in (37,38,39):
  for lo in (26,27,28):
    n=f"Copernicus_DSM_COG_30_N{la:02d}_00_E{lo:03d}_00_DEM"
    u=f"https://copernicus-dem-90m.s3.amazonaws.com/{n}/{n}.tif"
    r=requests.get(u,timeout=300)
    print(n,r.status_code,len(r.content)//1024,"KB",flush=True)
    if r.ok: open(f"ham/dem/{n}.tif","wb").write(r.content)
