// Servis çalışanı: sayfayı çevrimdışı açar.
// Kabuk (sayfa, stil, modüller, kilit.js) önbelleğe alınır; veri önce ağdan, olmazsa son kopyadan gelir.
// Yerel dosyalar (sayfa, kilit.js, manifest, ikonlar) önce ağdan alınır, olmazsa önbellekten gelir;
// bu yüzden içerik güncellemesi için SURUM artırmak GEREKMEZ. SURUM yalnız eski önbellekleri temizlemek içindir.
const SURUM = "v2"; // v2: 3B harita yerine pano (three.js kalktı)
const KABUK = "kafamin-kabuk-" + SURUM;
const VERI = "kafamin-veri"; // sürümden bağımsız: sürüm değişince son veri kaybolmasın
const VERI_DOSYASI = "veri.sifreli.json";

const YEREL = ["./", "index.html", "stil.css", "kilit.js", "arayuz.js", "pano.js", "odak.js",
  "manifest.webmanifest", "ikon-180.png", "ikon-512.png"];
const FONT_SUNUCULARI = ["fonts.googleapis.com", "fonts.gstatic.com"];

self.addEventListener("install", (olay) => {
  olay.waitUntil((async () => {
    const onbellek = await caches.open(KABUK);
    // biri indirilemezse kurulum başarısız olur; yerel dosyalar HTTP önbelleğini atlayarak alınır
    await Promise.all(YEREL.map((y) => onbellek.add(new Request(y, { cache: "reload" }))));
    // Yazı tipleri isteğe bağlı: ulaşılamazsa kurulumu bozma
    try {
      await onbellek.add("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,600&family=DM+Sans:wght@400;500;700&display=swap");
    } catch (_) { /* sistem yazı tipi kullanılır */ }
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (olay) => {
  olay.waitUntil((async () => {
    for (const ad of await caches.keys()) {
      if (ad.startsWith("kafamin-kabuk-") && ad !== KABUK) await caches.delete(ad);
    }
    await self.clients.claim();
  })());
});

// Veri: önce ağ (HTTP önbelleğini atlayarak), olmazsa son iyi kopya.
async function veriGetir(istek) {
  const onbellek = await caches.open(VERI);
  try {
    const yanit = await fetch(istek, { cache: "no-store" });
    if (yanit.ok) await onbellek.put(istek, yanit.clone());
    return yanit;
  } catch (hata) {
    const eski = await onbellek.match(istek, { ignoreSearch: true });
    if (eski) return eski;
    throw hata;
  }
}

// Yerel kabuk: önce ağ (her başarılı yanıt önbelleği günceller), ağ yoksa ya da yanıt ok değilse önbellek.
async function yerelGetir(istek, anahtar) {
  const onbellek = await caches.open(KABUK);
  try {
    const yanit = await fetch(istek, { cache: "no-cache" });
    if (yanit.ok) {
      await onbellek.put(anahtar, yanit.clone());
      return yanit;
    }
  } catch (_) { /* çevrimdışı: önbelleğe düş */ }
  const eski = await onbellek.match(anahtar, { ignoreSearch: true });
  if (eski) return eski;
  return fetch(istek);
}

// Diğerleri (yazı tipleri): önce önbellek; yoksa ağdan al, yazı tipiyse sakla.
async function onbellekOnce(istek) {
  const bulunan = await caches.match(istek, { ignoreSearch: true });
  if (bulunan) return bulunan;
  const yanit = await fetch(istek);
  const url = new URL(istek.url);
  if (FONT_SUNUCULARI.includes(url.hostname) && (yanit.ok || yanit.type === "opaque")) {
    const onbellek = await caches.open(KABUK);
    await onbellek.put(istek, yanit.clone());
  }
  return yanit;
}

self.addEventListener("fetch", (olay) => {
  const istek = olay.request;
  if (istek.method !== "GET") return;
  const url = new URL(istek.url);
  if (url.origin === self.location.origin && url.pathname.endsWith("/" + VERI_DOSYASI)) {
    olay.respondWith(veriGetir(istek));
    return;
  }
  if (istek.mode === "navigate") {
    // Sayfa açılışı: hep index.html (çevrimdışıyken de çalışsın)
    olay.respondWith(yerelGetir(istek, new URL("index.html", self.location).href));
    return;
  }
  if (url.origin === self.location.origin) {
    olay.respondWith(yerelGetir(istek, istek.url));
    return;
  }
  olay.respondWith(onbellekOnce(istek));
});
