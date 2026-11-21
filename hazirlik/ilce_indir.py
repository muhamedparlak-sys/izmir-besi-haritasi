import requests
q='[out:json][timeout:300];area["ISO3166-2"="TR-35"]->.a;relation(area.a)["boundary"="administrative"]["admin_level"="6"];out geom;'
r=requests.post("https://overpass-api.de/api/interpreter",data={"data":q},headers={"User-Agent":"izmir-besi-haritasi/1.0"},timeout=600)
open("ham/ilce.json","wb").write(r.content); print(r.status_code,len(r.content)//1024)
