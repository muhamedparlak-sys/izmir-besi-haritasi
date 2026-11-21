# İzmir besi çiftliği yer seçimi haritası

İzmir'de besi çiftliği kurmaya uygun olabilecek alanların **ön eleme** haritası. Haritayı açmak için `index.html` (GitHub Pages bağlantısı) yeterlidir.

## Ne gösteriyor?

- **A sınıfı (koyu yeşil):** resmî yola en çok 250 m, elektriğe çok yakın (OG hattına ≤500 m, trafo merkezine ≤3 km ya da köye ≤1 km).
- **B sınıfı (açık yeşil):** resmî yola en çok 250 m, elektriğe orta mesafede (1,5 km / 6 km / 2 km).
- Dışarıda bırakılanlar: havalimanları ve 3 km çevresi; askeri alanlar ve 500 m çevresi; il/ilçe merkezlerinin 3 km çevresi ve büyükşehir merkez ilçeleri; sit, tabiat ve yaban hayatı koruma alanları; olası büyük ovalar ve DSİ sulama alanları; kıyıdan 300 m; yerleşim alanları ve 300 m çevresi; göl/baraj ve 100 m çevresi; yüksek gerilim hattı bandı (40 m); eğimi %15'ten fazla yerler; Çevre Düzeni Planı'nda tarım arazisi olmayan alanlar (orman, mera, sanayi vb.).

Bir alana tıklayınca yola, elektriğe, köye ve kıyıya olan mesafeler ile TKGM parsel sorgu ve Google Haritalar bağlantıları çıkar.

## Sınırlılıklar

- **Büyük ova sınırları** resmî sayısal veri olarak yayımlanmadığı için düz alüvyal tabanlardan (eğim <%2, kot <250 m, ≥15 km²) ve DSİ sulama alanlarından **tahmin** edildi. Parsel için il tarım ve orman müdürlüğünden teyit alınmalı.
- **Kıyı kenar çizgisi** yerine OpenStreetMap kıyı çizgisinden 300 m tampon kullanıldı.
- **Sit alanları** ÇDP 1/100.000 görüntüsünden ve tabiat varlıkları verisinden üretildi; kesin sınır için Kültür Varlıkları ve Tabiat Varlıkları sorgusu yapılmalı.
- **Orta gerilim hatları** OpenStreetMap'te çok eksik; bu yüzden köy ve trafo merkezi yakınlığı da elektrik göstergesi olarak kullanıldı.
- **Kadastral yol:** yollar OpenStreetMap'ten. İzmir BB Kent Rehberi'ndeki yol orta hattı ve ada/parsel katmanları herkese açık bir veri servisi olarak sunulmadığı için kullanılmadı; parselin kadastral yola cephesi TKGM parsel sorgusundan kontrol edilmeli.
- İçme suyu havzası koruma bantları (Tahtalı, Gördes vb.) elemeye katılmadı; "Çevre Düzeni Planı (canlı)" katmanından ve ilgili idareden kontrol edin.

## Kaynaklar

- Çevre, Şehircilik ve İklim Değişikliği Bakanlığı, İzmir-Manisa Planlama Bölgesi 1/100.000 ÖÇ Çevre Düzeni Planı (TUCBS WMS)
- Tabiat varlıkları sit ve korunan alan verisi
- © OpenStreetMap katkıcıları (yollar, enerji hatları, kıyı, yerleşim, ilçe sınırları)
- Copernicus GLO-90 sayısal yükseklik modeli

## Yeniden üretmek

`hazirlik/` klasöründeki betikler sırayla çalıştırılır (Python 3, geopandas, rasterio, scipy):

```
python osm_indir.py
python dem_indir.py
python ilce_indir.py
python cdp_indir.py
python katmanlar.py
python cdp.py
python analiz.py
```

Ölçütler `analiz.py` içindeki `KRITER` sözlüğündedir; değiştirip `analiz.py` yeniden çalıştırılırsa `veri/` güncellenir.
