"""OSM, tabiat sit ve DEM katmanlarını ortak 50 m ızgaraya rasterleştirir -> ara/katmanlar.npz"""
import glob

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling
from scipy import ndimage

from ortak import ARA, CRS, HUCRE, HAM, osm, yol_geom, izmir_siniri, utm, izgara

TABIAT = r"C:\Users\muham\Downloads\arsandan\data"
TABIAT_DOSYALAR = ["tabiat_sit_derece1", "tabiat_sit_derece2", "tabiat_sit_derece3", "tabiat_sit_belirsiz",
                   "tabiat_oneri_sit", "tabiat_koruma_alani", "tabiat_park", "tabiat_yaban_hayati", "tabiat_anit"]


def ras(geoms, tr, shape, all_touched=True):
    geoms = [g for g in geoms if g is not None and not g.is_empty]
    if not geoms:
        return np.zeros(shape, bool)
    return rasterize(((g, 1) for g in geoms), out_shape=shape, transform=tr,
                     all_touched=all_touched, dtype="uint8").astype(bool)


def mesafe(mask):
    """Her hücrenin en yakın True hücreye uzaklığı (m)."""
    if not mask.any():
        return np.full(mask.shape, 1e9, "float32")
    return (ndimage.distance_transform_edt(~mask) * HUCRE).astype("float32")


def osm_utm(ad, filtre=lambda e: True):
    out = []
    for e in osm(ad):
        if filtre(e):
            g = yol_geom(e)
            if g is not None and not g.is_empty:
                out.append(utm(g))
    return out


def main():
    sinir = utm(izmir_siniri())
    tr, shape = izgara(sinir)
    print("ızgara", shape, flush=True)
    k = {}
    k["sinir"] = ras([sinir], tr, shape, all_touched=False)

    yollar = osm_utm("yol")
    k["d_yol"] = mesafe(ras(yollar, tr, shape))
    print("yol", len(yollar), flush=True)

    elk = osm("elektrik")
    tag = lambda e: e.get("tags", {}).get("power")
    hv = [utm(yol_geom(e)) for e in elk if tag(e) in ("line", "cable") and e["type"] == "way"]
    og = [utm(yol_geom(e)) for e in elk if tag(e) == "minor_line"]
    tm = [utm(yol_geom(e)).centroid for e in elk if tag(e) == "substation"]
    k["hv"] = ras([g.buffer(40) for g in hv], tr, shape)          # YG hattı altı/koruma bandı
    k["d_hv"] = mesafe(ras(hv, tr, shape))
    k["d_og"] = mesafe(ras(og, tr, shape))
    k["d_tm"] = mesafe(ras(tm, tr, shape))

    yer = osm("yerlesim")
    koy = [utm(yol_geom(e)) for e in yer if e["type"] == "node"
           and e.get("tags", {}).get("place") in ("village", "hamlet", "town", "city", "suburb", "neighbourhood")]
    konut = [utm(yol_geom(e)) for e in yer if e["type"] != "node"]
    k["d_koy"] = mesafe(ras(koy, tr, shape))
    k["konut"] = ras([g for g in konut if g.geom_type in ("Polygon", "MultiPolygon")], tr, shape, all_touched=False)
    k["d_konut"] = mesafe(k["konut"])

    kiyi = osm_utm("kiyi")
    k["d_kiyi"] = mesafe(ras(kiyi, tr, shape))
    su = osm_utm("su")
    k["su"] = ras([g for g in su if g.geom_type in ("Polygon", "MultiPolygon")], tr, shape, all_touched=False)
    k["d_akarsu"] = mesafe(ras([g for g in su if g.geom_type == "LineString"], tr, shape))
    print("osm tamam", flush=True)

    tab = []
    for f in TABIAT_DOSYALAR:
        g = gpd.read_file(f"{TABIAT}/{f}.geojson").cx[25.9:28.9, 37.5:39.7].to_crs(CRS)
        tab += [x.buffer(0) for x in g.geometry if x is not None]
    k["tabiat"] = ras(tab, tr, shape, all_touched=False)
    print("tabiat", len(tab), flush=True)

    srcs = [rasterio.open(p) for p in glob.glob(str(HAM / "dem" / "*.tif"))]
    mos, mtr = merge(srcs)
    dem = np.full(shape, np.nan, "float32")
    reproject(mos[0], dem, src_transform=mtr, src_crs="EPSG:4326", dst_transform=tr, dst_crs=CRS,
              resampling=Resampling.bilinear, dst_nodata=np.nan)
    gy, gx = np.gradient(dem, HUCRE)
    k["dem"] = dem
    k["egim"] = (np.hypot(gx, gy) * 100).astype("float32")   # yüzde eğim
    print("dem tamam", flush=True)

    np.savez_compressed(ARA / "katmanlar.npz", transform=np.array(tr)[:6], **k)
    print("kaydedildi")


if __name__ == "__main__":
    main()
