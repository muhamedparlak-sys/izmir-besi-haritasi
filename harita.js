/* İzmir besi çiftliği aday alanları — Leaflet haritası */
const KOYU = { yasak: "#3d0c14", merkez: "#1c1a33", yerlesim: "#262626", orman: "#16301d", mera: "#3b3519", egim: "#3a2a26", diger: "#2c3138" };
const RENK = { A: "#1d6b38", B: "#8cc56f", sit: "#c8463c", ova: "#e7b622", kiyi: "#3b7fc4", elk: "#7a3cc4" };
const CDP_WMS = "https://tucbs-public-api.csb.gov.tr/csb_cdp_im_wms";

const harita = L.map("harita", { zoomControl: false, preferCanvas: true }).setView([38.45, 27.35], 9);
L.control.zoom({ position: "topright" }).addTo(harita);
L.control.scale({ imperial: false, position: "bottomright" }).addTo(harita);

const altlik = {
  "Sokak haritası": L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: "© OpenStreetMap katkıcıları",
  }),
  "Uydu": L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19, attribution: "Esri, Maxar, Earthstar Geographics",
  }),
  "Topoğrafya": L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
    maxZoom: 17, attribution: "© OpenTopoMap (CC-BY-SA)",
  }),
};
altlik["Sokak haritası"].addTo(harita);
L.control.layers(altlik, null, { position: "topright" }).addTo(harita);

const katman = {
  cdp: L.tileLayer.wms(CDP_WMS, {
    layers: "2", format: "image/png", transparent: true, version: "1.3.0", opacity: 1,
    attribution: "ÇDP © Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
  }),
};

const sayi = (n) => (n == null ? "–" : n.toLocaleString("tr-TR"));
const km = (m) => (m == null ? "–" : m >= 1000 ? `${(m / 1000).toLocaleString("tr-TR", { maximumFractionDigits: 1 })} km` : `${m} m`);

function adayPopup(p, latlng) {
  const lat = latlng.lat.toFixed(5);
  const lng = latlng.lng.toFixed(5);
  const rozet = p.sinif === "A" ? RENK.A : "#5d9a44";
  return `<div class="pop">
    <span class="rozet" style="background:${rozet}">${p.sinif} sınıfı</span>
    <h3>Aday ${p.no} · ${p.ilce}</h3>
    <div class="kucuk">${sayi(p.alan_ha)} hektar · ort. eğim %${p.egim_ort} · kot ~${sayi(p.kot_m)} m</div>
    <table>
      <tr><td>Haritalı yola</td><td>${km(p.yol_m)}</td></tr>
      <tr><td>OG elektrik hattına</td><td>${km(p.og_hat_m)}</td></tr>
      <tr><td>Trafo merkezine</td><td>${km(p.trafo_merkezi_m)}</td></tr>
      <tr><td>Köy/mahalle merkezine</td><td>${km(p.koy_m)}</td></tr>
      <tr><td>YG hattına</td><td>${km(p.yg_hat_m)}</td></tr>
      <tr><td>Kıyıya</td><td>${km(p.kiyi_m)}</td></tr>
    </table>
    <div class="kucuk" style="margin-bottom:6px">Kadastral yol cephesini TKGM'den parsel parsel kontrol edin.</div>
    <div class="baglanti">
      <a href="https://parselsorgu.tkgm.gov.tr/#ara/cografi/${lat}/${lng}" target="_blank" rel="noopener">TKGM parsel</a>
      <a href="https://www.google.com/maps?q=${lat},${lng}&t=k" target="_blank" rel="noopener">Google Haritalar</a>
    </div>
  </div>`;
}

let adayVeri = null;
const adayKatman = { A: L.layerGroup(), B: L.layerGroup() };

function adaylariCiz() {
  const ilce = document.getElementById("ilce").value;
  const minHa = Number(document.getElementById("minHa").value);
  let adet = 0;
  let ha = 0;
  adayKatman.A.clearLayers();
  adayKatman.B.clearLayers();
  const secili = adayVeri.features.filter(
    (f) => (!ilce || f.properties.ilce === ilce) && f.properties.alan_ha >= minHa,
  );
  for (const f of secili) {
    const s = f.properties.sinif;
    const gorunur = harita.hasLayer(adayKatman[s]);
    L.geoJSON(f, {
      style: { color: RENK[s], weight: 1.2, fillColor: RENK[s], fillOpacity: s === "A" ? 0.6 : 0.5 },
    })
      .on("click", (e) => L.popup().setLatLng(e.latlng).setContent(adayPopup(f.properties, e.latlng)).openOn(harita))
      .addTo(adayKatman[s]);
    if (gorunur) {
      adet += 1;
      ha += f.properties.alan_ha;
    }
  }
  document.getElementById("sayiAday").textContent = sayi(adet);
  document.getElementById("sayiHa").textContent = sayi(Math.round(ha));
  return secili;
}

function ilceyeGit() {
  const secili = adaylariCiz();
  const ilce = document.getElementById("ilce").value;
  if (ilce && katman.ilce) {
    katman.ilce.eachLayer((l) => {
      if (l.feature.properties.ad === ilce) harita.fitBounds(l.getBounds(), kenarPayi());
    });
  } else if (!ilce && katman.ilce) {
    tumIzmir();
  }
}

function kenarPayi() {
  const genis = window.innerWidth > 640;
  return { paddingTopLeft: [genis ? 360 : 10, 10], paddingBottomRight: [10, genis ? 10 : 60] };
}

function tumIzmir() {
  harita.fitBounds(katman.ilce.getBounds(), kenarPayi());
}

async function yukle(ad) {
  const r = await fetch(`veri/${ad}.geojson`);
  if (!r.ok) throw new Error(`${ad} yüklenemedi (${r.status})`);
  return r.json();
}

async function basla() {
  try {
    const [aday, sit, ova, kiyi, elk, ilce, kotu] = await Promise.all(
      ["adaylar", "sit", "ova", "kiyi", "elektrik", "sinir", "kullanilamaz"].map(yukle),
    );
    katman.kotu = L.geoJSON(kotu, {
      style: (f) => ({ stroke: false, fillColor: KOYU[f.properties.kod], fillOpacity: 0.78 }),
      onEachFeature: (f, l) => l.bindTooltip(`Uygun değil: ${f.properties.ad}`, { sticky: true }),
    });
    const alanStil = (renk, op) => ({ color: renk, weight: 0.8, fillColor: renk, fillOpacity: op, interactive: true });
    const etiketli = (f, l) => l.bindTooltip(f.properties.ad, { sticky: true });

    katman.ilce = L.geoJSON(ilce, {
      style: { color: "#555", weight: 1, fill: false, dashArray: "4 3", interactive: false },
    });
    katman.ova = L.geoJSON(ova, { style: alanStil(RENK.ova, 0.35), onEachFeature: etiketli });
    katman.kiyi = L.geoJSON(kiyi, { style: alanStil(RENK.kiyi, 0.25), onEachFeature: etiketli });
    katman.sit = L.geoJSON(sit, { style: alanStil(RENK.sit, 0.3), onEachFeature: etiketli });
    katman.elektrik = L.geoJSON(elk, {
      style: (f) => ({
        color: RENK.elk, weight: f.properties.tur === "OG hattı" ? 1.5 : 2.2,
        dashArray: f.properties.tur === "OG hattı" ? "3 3" : null, opacity: 0.8,
      }),
      pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 3.5, color: "#fff", weight: 1, fillColor: RENK.elk, fillOpacity: 0.9 }),
      onEachFeature: (f, l) => {
        const p = f.properties;
        const gerilim = p.gerilim ? ` · ${p.gerilim.split(";").map((v) => `${Number(v) / 1000} kV`).join(", ")}` : "";
        l.bindTooltip(`${p.tur}${gerilim}${p.ad ? ` · ${p.ad}` : ""}`, { sticky: true });
      },
    });

    adayVeri = aday;
    katman.A = adayKatman.A;
    katman.B = adayKatman.B;

    const ilceler = [...new Set(aday.features.map((f) => f.properties.ilce))].filter((x) => x !== "?").sort((a, b) => a.localeCompare(b, "tr"));
    const sec = document.getElementById("ilce");
    for (const ad of ilceler) sec.add(new Option(ad, ad));

    document.querySelectorAll("input[data-k]").forEach((cb) => {
      const k = katman[cb.dataset.k];
      if (cb.checked) k.addTo(harita);
      cb.addEventListener("change", () => {
        if (cb.checked) k.addTo(harita); else harita.removeLayer(k);
        if (cb.dataset.k === "A" || cb.dataset.k === "B") adaylariCiz();
        katmanSirasi();
      });
    });
    katmanSirasi();
    adaylariCiz();
    tumIzmir();
  } catch (hata) {
    document.getElementById("sayiAday").textContent = "!";
    alert(`Veri yüklenemedi: ${hata.message}`);
  }
}

function katmanSirasi() {
  ["kotu", "ova", "kiyi", "sit", "elektrik", "B", "A"].forEach((k) => {
    const l = katman[k];
    if (l && harita.hasLayer(l)) l.eachLayer?.((x) => x.bringToFront?.());
  });
}

document.getElementById("ilce").addEventListener("change", ilceyeGit);
document.getElementById("minHa").addEventListener("input", (e) => {
  document.getElementById("minHaYazi").textContent = `${e.target.value} ha`;
  adaylariCiz();
});

function panelGoster(acik) {
  document.getElementById("panel").classList.toggle("gizli", !acik);
}
if (window.matchMedia("(max-width: 640px)").matches) panelGoster(false);

basla();
