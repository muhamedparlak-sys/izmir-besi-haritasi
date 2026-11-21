"""Besi çiftliği aday alanları -> ../veri/*.geojson

Ölçütler (KRITER sözlüğünde, değiştirip yeniden çalıştırılabilir):
  dışlananlar: sit + koruma alanları, olası büyük ova + DSİ sulama alanı, kıyı bandı,
               yerleşim + tampon, göl/baraj, YG hattı bandı, dik yamaç, ÇDP'de tarım dışı alanlar
  aranan:      resmi yola yakınlık + elektriğe yakınlık
"""
import json

import numpy as np
from affine import Affine
from rasterio.features import shapes
from scipy import ndimage
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

from ortak import ARA, KOK, HUCRE, osm, yol_geom, utm, wgs
from cdp import SINIF

CIKTI = KOK.parent / "veri"
CIKTI.mkdir(exist_ok=True)

KRITER = {
    "kiyi_bandi_m": 300,        # kıyı çizgisinden (KKÇ + 100 m sahil şeridi için yaklaşık pay)
    "yerlesim_tampon_m": 300,   # yerleşik alan sınırından
    "yg_bandi_m": 40,           # yüksek gerilim hattı koruma bandı (katmanlar.py)
    "gol_tampon_m": 100,
    "max_egim_yuzde": 15,
    "ova_egim_yuzde": 2,        # olası büyük ova: düz taban
    "ova_max_kot_m": 250,
    "ova_min_km2": 15,
    "yol_m": 250,            # yola cepheli parsel derinliği için
    "elk_iyi": {"og_m": 500, "tm_m": 3000, "koy_m": 1000},
    "elk_orta": {"og_m": 1500, "tm_m": 6000, "koy_m": 2000},
    "min_alan_ha": 3,
    "havalimani_tampon_m": 3000,   # kuş çarpması / mania; havalimanı sınırından
    "askeri_tampon_m": 500,        # askeri alan sınırından (yasak bölge yaklaşık)
    "sehir_merkezi_tampon_m": 3000,  # il/ilçe merkezi (city/town) noktasından
    "merkez_ilceler": ["Konak", "Karşıyaka", "Bornova", "Buca", "Bayraklı", "Çiğli", "Gaziemir",
                       "Balçova", "Narlıdere", "Karabağlar", "Güzelbahçe"],
}


def yasak_ve_merkez(k):
    """Havalimanı, askeri alan ve şehir merkezi maskeleri (OSM + ilçe sınırı)."""
    from katmanlar import ras, mesafe
    K = KRITER
    tr = Affine(*k["transform"])
    shp = k["sinir"].shape
    yasak = [e for e in osm("yasak") if e["type"] != "node"]
    tag = lambda e: e.get("tags", {})
    havalimani = [utm(g) for e in yasak if tag(e).get("aeroway") == "aerodrome" and (g := yol_geom(e)) is not None]
    askeri = [utm(g) for e in yasak if tag(e).get("aeroway") != "aerodrome" and (g := yol_geom(e)) is not None]
    hav = mesafe(ras([g.buffer(0) for g in havalimani], tr, shp)) <= K["havalimani_tampon_m"]
    ask = mesafe(ras([g.buffer(0) for g in askeri], tr, shp)) <= K["askeri_tampon_m"]
    merkez_nokta = [utm(yol_geom(e)) for e in osm("yerlesim")
                    if e["type"] == "node" and tag(e).get("place") in ("city", "town")]
    mer = mesafe(ras(merkez_nokta, tr, shp)) <= K["sehir_merkezi_tampon_m"]
    ilce = [g for n, g in ilceler() if n in K["merkez_ilceler"]]
    mer |= ras(ilce, tr, shp, all_touched=False)
    return hav | ask, mer


def olasi_ova(k, c):
    K = KRITER
    duz = (k["egim"] < K["ova_egim_yuzde"]) & (k["dem"] < K["ova_max_kot_m"])
    duz &= np.isin(c["l2"], [SINIF["tarim"], SINIF["thga"]]) | c["sulama"]
    duz = ndimage.binary_opening(duz, iterations=2)
    duz = ndimage.binary_closing(duz, iterations=3)
    lab, n = ndimage.label(duz)
    alan = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1)) * HUCRE ** 2 / 1e6
    buyuk = np.zeros(n + 1, bool)
    buyuk[1:] = alan >= K["ova_min_km2"]
    return ndimage.binary_fill_holes(buyuk[lab])


def maskeler(k, c):
    K = KRITER
    m = {}
    m["sit"] = c["sit"] | c["koruma"] | k["tabiat"]
    m["ova"] = olasi_ova(k, c) | c["sulama"]
    m["kiyi"] = k["d_kiyi"] <= K["kiyi_bandi_m"]
    m["yerlesim"] = k["konut"] | (k["d_konut"] <= K["yerlesim_tampon_m"]) | (c["l2"] == SINIF["yerlesim"])
    su = k["su"] | (c["l2"] == SINIF["su"])
    m["su"] = (ndimage.distance_transform_edt(~su) * HUCRE <= K["gol_tampon_m"]) if su.any() else su
    m["yg"] = k["hv"]
    m["egim"] = k["egim"] > K["max_egim_yuzde"]
    m["cdp_disi"] = ~np.isin(c["l2"], [SINIF["tarim"], SINIF["thga"]])
    m["yasak"], m["merkez"] = yasak_ve_merkez(k)
    return m


def elektrik(k, e):
    return (k["d_og"] <= e["og_m"]) | (k["d_tm"] <= e["tm_m"]) | (k["d_koy"] <= e["koy_m"])


def poligonla(mask, tr, min_ha, sade=25):
    out = []
    for g, v in shapes(mask.astype("uint8"), mask=mask, transform=tr, connectivity=8):
        p = shape(g)
        if p.area / 1e4 >= min_ha:
            out.append(p.simplify(sade, preserve_topology=True))
    return out


def ilceler():
    out = []
    for e in osm("ilce"):
        if e["type"] == "relation":
            g = yol_geom(e)
            if g is not None:
                out.append((e["tags"].get("name", "?"), utm(g)))
    return out


def ozet(p, k, tr):
    """Poligon içindeki hücrelerde ortalama/en küçük mesafeler."""
    inv = ~tr
    minx, miny, maxx, maxy = p.bounds
    c0, r1 = inv * (minx, miny)
    c1, r0 = inv * (maxx, maxy)
    r0, r1, c0, c1 = int(r0), int(np.ceil(r1)), int(c0), int(np.ceil(c1))
    from rasterio.features import geometry_mask
    sub_tr = tr * Affine.translation(c0, r0)
    msk = ~geometry_mask([p], (r1 - r0, c1 - c0), sub_tr, all_touched=False)
    sl = (slice(r0, r1), slice(c0, c1))
    f = lambda a, fn: int(round(float(fn(a[sl][msk])))) if msk.any() else None
    return {
        "yol_m": f(k["d_yol"], np.min),
        "og_hat_m": f(k["d_og"], np.min),
        "trafo_merkezi_m": f(k["d_tm"], np.min),
        "koy_m": f(k["d_koy"], np.min),
        "yerlesime_m": f(k["d_konut"], np.max),
        "yg_hat_m": f(k["d_hv"], np.min),
        "kiyi_m": f(k["d_kiyi"], np.min),
        "egim_ort": round(float(k["egim"][sl][msk].mean()), 1) if msk.any() else None,
        "kot_m": f(k["dem"], np.mean),
    }


def yaz(ad, feats):
    fc = {"type": "FeatureCollection", "features": feats}
    s = json.dumps(fc, ensure_ascii=False, separators=(",", ":"))
    (CIKTI / f"{ad}.geojson").write_text(s, encoding="utf-8")
    print(ad, len(feats), "öğe", len(s) // 1024, "KB")


def wgs_yuvarla(g, nd=5):
    d = mapping(wgs(g))
    def r(x):
        return [r(y) for y in x] if isinstance(x[0], (list, tuple)) else [round(x[0], nd), round(x[1], nd)]
    d["coordinates"] = r(d["coordinates"])
    return d


KARANLIK = [  # (kod, ad) — öncelik sırası: bir hücre ilk uyan sınıfa girer
    ("yasak", "Havalimanı (3 km) ve askeri alan (500 m)"),
    ("merkez", "Şehir merkezi ve merkez ilçeler"),
    ("yerlesim", "Yerleşim, sanayi ve çevresi"),
    ("orman", "Orman ve makilik"),
    ("mera", "Mera ve çayır"),
    ("egim", "Dik yamaç (eğim > %15)"),
    ("diger", "Su, YG hattı ve planda tarım dışı alan"),
]


def kullanilamaz(m, k, c, tr):
    """Besi çiftliğine yaramayan kara alanları (sit/ova/kıyı ayrı katmanlarda)."""
    kara = k["sinir"] & (k["dem"] > 0)
    kalan = kara.copy()
    maske = {
        "yasak": m["yasak"],
        "merkez": m["merkez"],
        "yerlesim": m["yerlesim"],
        "orman": c["l2"] == SINIF["orman"],
        "mera": c["l2"] == SINIF["mera"],
        "egim": m["egim"],
        "diger": m["su"] | m["yg"] | m["cdp_disi"],
    }
    feats = []
    for kod, ad in KARANLIK:
        sec = maske[kod] & kalan
        kalan &= ~sec
        sec = ndimage.binary_closing(sec, iterations=1) & kara      # az yumuşatma: gerçek sınıra yakın
        for p in poligonla(sec, tr, 3, sade=35):
            feats.append({"type": "Feature", "properties": {"kod": kod, "ad": ad}, "geometry": wgs_yuvarla(p, 4)})
    return feats


def main():
    k = dict(np.load(ARA / "katmanlar.npz"))
    c = dict(np.load(ARA / "cdp.npz"))
    tr = Affine(*k["transform"])
    m = maskeler(k, c)
    kara = k["sinir"] & ~np.isnan(k["dem"])
    dis = np.zeros_like(kara)
    for ad, v in m.items():
        print(f"  dışlanan {ad:9s} {(v & kara).sum() * HUCRE**2 / 1e6:8.0f} km2")
        dis |= v
    uygun = kara & ~dis & (k["d_yol"] <= KRITER["yol_m"])
    a = uygun & elektrik(k, KRITER["elk_iyi"])
    b = uygun & elektrik(k, KRITER["elk_orta"]) & ~a
    print("A", a.sum() * HUCRE**2 / 1e6, "km2  B", b.sum() * HUCRE**2 / 1e6, "km2")

    ilc = ilceler()
    feats = []
    for sinif, mask in (("A", a), ("B", b)):
        for p in poligonla(mask, tr, KRITER["min_alan_ha"]):
            ilce = next((n for n, g in ilc if g.intersects(p.representative_point())), "?")
            props = {"sinif": sinif, "ilce": ilce, "alan_ha": round(p.area / 1e4, 1), **ozet(p, k, tr)}
            feats.append({"type": "Feature", "properties": props, "geometry": wgs_yuvarla(p)})
    feats.sort(key=lambda f: (f["properties"]["sinif"], -f["properties"]["alan_ha"]))
    for i, f in enumerate(feats, 1):
        f["properties"]["no"] = i
    yaz("adaylar", feats)

    for ad, etiket in (("sit", "Sit ve koruma alanı"), ("ova", "Olası büyük ova / DSİ sulama alanı (yaklaşık)"),
                       ("kiyi", f"Kıyı bandı ({KRITER['kiyi_bandi_m']} m, yaklaşık)")):
        mask = ndimage.binary_closing(m[ad] & k["sinir"], iterations=1)
        ps = poligonla(mask, tr, 5, sade=60)
        yaz(ad, [{"type": "Feature", "properties": {"ad": etiket}, "geometry": wgs_yuvarla(p, 4)} for p in ps])

    yaz("kullanilamaz", kullanilamaz(m, k, c, tr))

    elk = osm("elektrik")
    ef = []
    for e in elk:
        t = e.get("tags", {})
        g = yol_geom(e)
        if g is None:
            continue
        tur = {"line": "YG hattı", "cable": "YG kablo", "minor_line": "OG hattı", "substation": "Trafo merkezi"}.get(t.get("power"))
        if t.get("power") == "substation":
            g = g.centroid
        ef.append({"type": "Feature", "properties": {"tur": tur, "gerilim": t.get("voltage", ""), "ad": t.get("name", "")},
                   "geometry": wgs_yuvarla(utm(g)) if g.geom_type != "Point" else {"type": "Point", "coordinates": [round(g.x, 5), round(g.y, 5)]}})
    yaz("elektrik", ef)

    bnd = unary_union([g for _, g in ilc]).simplify(50)
    yaz("sinir", [{"type": "Feature", "properties": {"ad": n}, "geometry": wgs_yuvarla(g.simplify(50), 4)} for n, g in ilc])
    (CIKTI / "kriter.json").write_text(json.dumps(KRITER, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
