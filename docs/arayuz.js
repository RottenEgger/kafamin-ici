// Arayüz: pano modelini sayfaya çizer (özet → takıldığım yerler → pano).
// Veriden gelen her yazı textContent ile girer (innerHTML yok): not metinleri güvenilmez sayılır.
import { panoModeli, suz } from "./pano.js";

// Küçük yardımcı: <etiket class="sinif">metin</etiket>
function el(etiket, sinif, metin) {
  const e = document.createElement(etiket);
  if (sinif) e.className = sinif;
  if (metin !== undefined && metin !== null) e.textContent = metin;
  return e;
}

const gunYazisi = (g) => (g === 0 ? "bugün" : `${g}g`);

let VERI = null;
let MODEL = null;
let secim = "hepsi"; // özet kutusu süzgeci

// Bir öğeye dokununca odak açılır (Görev 6'da gerçek odak katmanı gelir).
export function odagiAc(id) {
  console.info("odak:", id);
}

function ozetCiz(kok, ozet) {
  const kutu = el("div", "ozet");
  const kutular = [
    ["calisilan", ozet.calisilan, "çalıştığın proje · 7 gün"],
    ["hepsi", ozet.siradaki, "sıradaki adım"],
    ["bekleyen", ozet.bekleyen, ozet.enEskiGun !== null ? `bekleyen · en eskisi ${ozet.enEskiGun} gün` : "bekleyen"],
  ];
  for (const [ad, sayi, yazi] of kutular) {
    const b = el("button", ad);
    b.type = "button";
    // "sıradaki" kutusu süzgeci kaldırır; diğerleri aç/kapa
    b.setAttribute("aria-pressed", String(ad !== "hepsi" && secim === ad));
    b.append(el("span", "sayi", String(sayi)), el("span", "ad", yazi));
    b.onclick = () => {
      secim = ad === "hepsi" || secim === ad ? "hepsi" : ad;
      ciz();
    };
    kutu.append(b);
  }
  kok.append(kutu);
}

function desenleriCiz(kok, desenler) {
  if (!desenler.length) return;
  const bolum = el("section", "takildigim");
  bolum.append(el("h2", "baslik-kucuk", "Takıldığım yerler"));
  const cipler = el("div", "cipler");
  for (const d of desenler) {
    const b = el("button", "desen", "⊘ " + d.ad);
    b.type = "button";
    b.append(el("span", "n", String(d.uyeSayisi)));
    b.onclick = () => odagiAc(d.id);
    cipler.append(b);
  }
  bolum.append(cipler);
  kok.append(bolum);
}

function isDugmesi(is) {
  const b = el("button", "is" + (is.unutulmus ? " unutulmus" : ""), "□ " + is.ad);
  b.type = "button";
  if (is.unutulmus && is.bekliyorGun !== null) b.append(el("span", "gun", `${is.bekliyorGun}g`));
  b.onclick = () => odagiAc(is.id);
  return b;
}

function satirCiz(p) {
  const satir = el("div", "satir");
  const ana = el("button", "ana");
  ana.type = "button";
  ana.style.setProperty("--alan", p.renk);
  ana.style.setProperty("--taze", String(p.tazelik));
  if (p.renk2) ana.style.setProperty("--alan2", p.renk2);

  const yap = el("span", "yap", p.sonGun !== null ? "✓ " + gunYazisi(p.sonGun) : "");
  if (p.son?.metin) yap.title = p.son.metin;
  const ad = el("span", "proje" + (p.renk2 ? " iki" : ""), p.ad);
  const sonraki = p.gizli ? el("span", "sonraki gizli", "🔒 gizli") : el("span", "sonraki", p.sonraki || "");
  ana.append(yap, ad, sonraki);
  ana.setAttribute("aria-label", `${p.ad}${p.sonraki ? ". Sıradaki: " + p.sonraki : ""}`);
  ana.onclick = () => odagiAc(p.id);
  satir.append(ana);

  if (p.fikir) {
    const f = el("button", "fikir", "✧ " + p.fikir.ad);
    f.type = "button";
    f.style.setProperty("--alan", p.renk);
    f.onclick = () => odagiAc(p.fikir.id);
    satir.append(f);
  }
  const parca = document.createDocumentFragment();
  parca.append(satir);
  if (p.yapilacaklar.length) {
    const isler = el("div", "isler");
    for (const is of p.yapilacaklar) isler.append(isDugmesi(is));
    if (p.fazla) isler.append(el("span", "fazla", `+${p.fazla}`));
    parca.append(isler);
  }
  return parca;
}

const CIP_ISARETI = { fikir: "✧ ", ders: "◈ ", kaynak: "◇ " };

function alanCiz(a) {
  const bolum = el("section", "alan");
  bolum.style.setProperty("--alan", a.renk);
  bolum.append(el("h2", "", a.ad));
  for (const p of a.projeler) bolum.append(satirCiz(p));

  if (a.yapilacaklar.length) {
    const liste = el("div", "liste");
    for (const is of a.yapilacaklar) liste.append(isDugmesi(is));
    bolum.append(liste);
  }
  if (a.yapilanlar.length) {
    const liste = el("div", "liste");
    liste.append(el("div", "baslik-kucuk", "✓ bu hafta"));
    for (const is of a.yapilanlar) {
      const b = el("button", "yapilan", "✓ " + is.ad);
      b.type = "button";
      b.onclick = () => odagiAc(is.id);
      liste.append(b);
    }
    bolum.append(liste);
  }
  if (a.cipler.length) {
    const cipler = el("div", "cipler");
    for (const c of a.cipler) {
      const b = el("button", "cip", (CIP_ISARETI[c.tur] || "") + c.ad);
      b.type = "button";
      b.onclick = () => odagiAc(c.id);
      cipler.append(b);
    }
    bolum.append(cipler);
  }
  return bolum;
}

function ciz() {
  const kok = document.getElementById("pano");
  kok.replaceChildren();
  ozetCiz(kok, MODEL.ozet);
  desenleriCiz(kok, MODEL.desenler);
  const gorunen = suz(MODEL, secim);
  if (!gorunen.alanlar.length) kok.append(el("p", "bos", "Burada gösterilecek bir şey yok."));
  else {
    const basliklar = el("div", "sutunlar");
    basliklar.setAttribute("aria-hidden", "true");
    for (const b of ["Yaptım", "Proje", "Sıradaki →", "Fikir"]) basliklar.append(el("span", "", b));
    kok.append(basliklar);
  }
  for (const a of gorunen.alanlar) kok.append(alanCiz(a));
}

export function baslat(veri) {
  VERI = veri;
  MODEL = panoModeli(veri);
  document.getElementById("tarih").textContent = MODEL.tarih;
  ciz();
}

export const veriyiAl = () => VERI;
