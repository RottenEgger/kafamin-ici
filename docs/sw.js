// Servis çalışanı: sayfayı çevrimdışı açar.
// Kabuk (sayfa, kilit.js, three.js) önbelleğe alınır; veri önce ağdan, olmazsa son kopyadan gelir.
// Kabuktaki bir şey değişince SURUM'u artır: eski kabuk önbelleği silinir.
const SURUM = "v1";
const KABUK = "kafamin-kabuk-" + SURUM;
const VERI = "kafamin-veri"; // sürümden bağımsız: sürüm değişince son veri kaybolmasın
const VERI_DOSYASI = "veri.sifreli.json";

const THREE = "https://cdn.jsdelivr.net/npm/three@0.160.0/";
// Sayfa açılırken gerçekten istenen modüller (ağ denetçisinden çıkarıldı).
const THREE_URLLERI = [
  "build/three.module.js",
  "examples/jsm/controls/OrbitControls.js",
  "examples/jsm/postprocessing/EffectComposer.js",
  "examples/jsm/postprocessing/RenderPass.js",
  "examples/jsm/postprocessing/UnrealBloomPass.js",
  "examples/jsm/postprocessing/OutputPass.js",
  "examples/jsm/postprocessing/Pass.js",
  "examples/jsm/postprocessing/ShaderPass.js",
  "examples/jsm/postprocessing/MaskPass.js",
  "examples/jsm/renderers/CSS2DRenderer.js",
  "examples/jsm/shaders/CopyShader.js",
  "examples/jsm/shaders/LuminosityHighPassShader.js",
  "examples/jsm/shaders/OutputShader.js",
].map((y) => THREE + y);

const YEREL = ["./", "index.html", "kilit.js", "manifest.webmanifest", "ikon-180.png", "ikon-512.png"];
const FONT_SUNUCULARI = ["fonts.googleapis.com", "fonts.gstatic.com"];

self.addEventListener("install", (olay) => {
  olay.waitUntil((async () => {
    const onbellek = await caches.open(KABUK);
    await onbellek.addAll([...YEREL, ...THREE_URLLERI]); // biri indirilemezse kurulum başarısız olur
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

// Diğerleri: önce önbellek; yoksa ağdan al, yazı tipiyse sakla.
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
    // Sayfa açılışı: kabuktaki index.html (çevrimdışıyken de çalışsın)
    olay.respondWith(
      caches.match("index.html", { ignoreSearch: true }).then((b) => b || fetch(istek))
    );
    return;
  }
  olay.respondWith(onbellekOnce(istek));
});
