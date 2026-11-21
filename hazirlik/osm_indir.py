import requests, json, time, sys
M=["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter","https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
H={"User-Agent":"izmir-besi-haritasi/1.0"}
AREA='area["ISO3166-2"="TR-35"]->.a;'
Q={
 "sinir":'[out:json][timeout:300];relation["ISO3166-2"="TR-35"];out geom;',
 "yol":f'[out:json][timeout:600];{AREA}way(area.a)["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$"];out geom;',
 "elektrik":f'[out:json][timeout:600];{AREA}(way(area.a)["power"~"^(line|minor_line|cable)$"];nwr(area.a)["power"="substation"];);out geom;',
 "kiyi":'[out:json][timeout:600];way["natural"="coastline"](37.7,26.1,39.5,28.6);out geom;',
 "yerlesim":f'[out:json][timeout:600];{AREA}(way(area.a)["landuse"~"^(residential|industrial|commercial|retail)$"];relation(area.a)["landuse"~"^(residential|industrial|commercial|retail)$"];node(area.a)["place"~"^(city|town|village|hamlet|suburb|neighbourhood)$"];);out geom;',
 "su":f'[out:json][timeout:600];{AREA}(way(area.a)["natural"="water"];relation(area.a)["natural"="water"];way(area.a)["waterway"~"^(river|canal)$"];);out geom;',
}
for k in (sys.argv[1:] or Q):
    for u in M:
        try:
            t=time.time(); r=requests.post(u,data={"data":Q[k]},headers=H,timeout=900)
            if r.ok and r.content.startswith(b'{'):
                open(f"ham/{k}.json","wb").write(r.content); print(k,u,len(r.content)//1024,"KB",int(time.time()-t),"s",flush=True); break
            print(k,u,"HTTP",r.status_code,r.text[:120],flush=True)
        except Exception as e: print(k,u,"ERR",e,flush=True)
