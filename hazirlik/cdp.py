"""ÇDP (İzmir-Manisa 1/100.000) WMS karolarını ızgaraya çevirir -> ara/cdp.npz

L2: arazi kullanımı rengi -> sınıf kodu (lejant renginden en yakın renk)
L5: enerji-sulama alanları, L7: diğer koruma alanları, L9: sit alanları
     (çizgi + tarama olarak çizildikleri için kapalı alanlar doldurulur)
"""
import numpy as np
from PIL import Image
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling
from scipy import ndimage

from ortak import ARA, CRS, HAM

W, S, E, N = 26.15, 37.70, 28.55, 39.45
NX = NY = 4
PX, PY = 1200, 874

LEJANT = {  # ad: (renk, sınıf)
    "tarim": [(211, 255, 190)],
    "thga": [(163, 255, 116)],                     # tarım ve hayvancılık geliştirme alanı
    "mera": [(154, 230, 0)],
    "orman": [(55, 168, 0), (165, 245, 124), (169, 255, 0), (110, 194, 0), (36, 116, 0), (36, 157, 31)],
    "yerlesim": [(138, 90, 36), (206, 169, 102), (255, 255, 0), (197, 0, 255), (169, 0, 230), (255, 169, 0),
                 (255, 190, 232), (255, 127, 127), (202, 99, 150), (255, 85, 0), (110, 168, 0), (190, 210, 255)],
    "su": [(163, 210, 255), (0, 110, 255), (116, 180, 255), (124, 182, 245), (184, 243, 228), (255, 255, 190)],
    "diger": [(206, 206, 206), (225, 225, 225), (180, 180, 180), (209, 255, 116), (255, 190, 190), (230, 0, 0),
              (124, 140, 245)],
}
SINIF = {ad: i + 1 for i, ad in enumerate(LEJANT)}   # 0 = veri yok


def mozaik(L):
    arr = np.zeros((PY * NY, PX * NX, 4), "uint8")
    for i in range(NX):
        for j in range(NY):
            im = np.array(Image.open(HAM / "cdp" / f"L{L}_{i}_{j}.png").convert("RGBA"))
            r0 = (NY - 1 - j) * PY
            arr[r0:r0 + PY, i * PX:(i + 1) * PX] = im
    return arr


def siniflandir(rgba):
    renkler, kodlar = [], []
    for ad, rl in LEJANT.items():
        for r in rl:
            renkler.append(r)
            kodlar.append(SINIF[ad])
    # servis katmanı %50 saydamlıkla beyaz üstüne çiziyor: görünen = (renk + 255) / 2
    renkler = (np.array(renkler, "int16") + 255) // 2
    kodlar = np.array(kodlar, "uint8")
    rgb = rgba[..., :3].astype("int16")
    out = np.zeros(rgba.shape[:2], "uint8")
    for r0 in range(0, rgb.shape[0], 500):           # bellek için parça parça
        blok = rgb[r0:r0 + 500]
        d = ((blok[..., None, :] - renkler[None, None]) ** 2).sum(-1)
        en = d.argmin(-1)
        ok = d.min(-1) < 15 ** 2
        out[r0:r0 + 500] = np.where(ok, kodlar[en], 0)
    out[rgba[..., 3] < 128] = 0
    # kenar yumuşatma piksellerini komşu çoğunluğuyla doldur
    bos = out == 0
    idx = ndimage.distance_transform_edt(bos, return_distances=False, return_indices=True)
    dolu = out[tuple(idx)]
    yakin = ndimage.distance_transform_edt(bos) <= 2
    return np.where(bos & yakin & (rgba[..., 3] >= 128), dolu, out)


def doldur(rgba):
    m = rgba[..., 3] > 40
    m = ndimage.binary_closing(m, iterations=2)
    return ndimage.binary_fill_holes(m)


def izgaraya(arr, tr_dst, shape):
    src_tr = from_origin(W, N, (E - W) / (PX * NX), (N - S) / (PY * NY))
    out = np.zeros(shape, arr.dtype)
    reproject(arr, out, src_transform=src_tr, src_crs="EPSG:4326", dst_transform=tr_dst, dst_crs=CRS,
              resampling=Resampling.nearest)
    return out


def main():
    k = np.load(ARA / "katmanlar.npz")
    from affine import Affine
    tr = Affine(*k["transform"])
    shape = k["sinir"].shape
    out = {"l2": izgaraya(siniflandir(mozaik("2")), tr, shape)}
    for L, ad in (("5", "sulama"), ("7", "koruma"), ("9", "sit")):
        out[ad] = izgaraya(doldur(mozaik(L)).astype("uint8"), tr, shape).astype(bool)
        print(ad, out[ad].sum() * 0.0025, "km2", flush=True)
    for ad, c in SINIF.items():
        print(ad, round(float(((out["l2"] == c) & k["sinir"]).sum() * 0.0025)), "km2")
    np.savez_compressed(ARA / "cdp.npz", **out)


if __name__ == "__main__":
    main()
