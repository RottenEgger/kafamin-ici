// Arayüz: pano modelini sayfaya çizer (özet → takıldığım yerler → pano).
// Veriden gelen her yazı textContent ile girer (innerHTML yok): not metinleri güvenilmez sayılır.
import { panoModeli, suz } from "./pano.js";
import { odakModeli, halkaKonumlari } from "./odak.js";
import { cekmeceKur } from "./cekmece.js";

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

// ---------------- Odak katmanı (21st "Radial Orbital Timeline"dan uyarlandı) ----------------
// Ortada seçilen öğe, etrafında bağları; kısa düz ipler, ipin üstünde bağın kısa adı.
// Sürekli dönme yok (okunabilirlik); yalnız açılışta düğümler merkezden halkaya yayılır.

const SVG = "http://www.w3.org/2000/svg";
const ETIKET_SINIRI = 22; // ip üstündeki başlığın en çok karakteri
const ETIKETLI_EN_FAZLA = 8; // bundan çok bağ varsa ip etiketleri gizlenir (dokununca çekmecede okunur)
const ALTIN = "#f4c86a";
const ACIK_IP = "rgba(255,255,255,.3)";

let odakKatmani = null;
let cekmece = null;
let yigin = []; // odak geçmişi (geri için)

const kisaBaslik = (b) => {
  const t = (b.baslik || "").replace(/^Kara deliğe çekilen: /, "");
  return t.length > ETIKET_SINIRI ? t.slice(0, ETIKET_SINIRI - 1).trimEnd() + "…" : t;
};

function katmaniKur() {
  odakKatmani = el("div", "odak");
  odakKatmani.hidden = true;
  odakKatmani.setAttribute("role", "dialog");
  odakKatmani.setAttribute("aria-modal", "true");
  const geri = el("button", "odak-geri", "← Panoya dön");
  geri.type = "button";
  geri.onclick = () => odagiKapat();
  const sahne = el("div", "odak-sahne");
  odakKatmani.append(geri, sahne);
  // Boşluğa dokunmak katmanı kapatır
  sahne.addEventListener("click", (olay) => { if (olay.target === sahne) odagiKapat(); });
  document.body.append(odakKatmani);
  const cekmeceKok = el("div", "cekmece-kok");
  document.body.append(cekmeceKok);
  cekmece = cekmeceKur(cekmeceKok);

  addEventListener("keydown", (olay) => {
    if (olay.key !== "Escape" || odakKatmani.hidden) return;
    if (cekmece.durum() === "tam") cekmece.kisalt();
    else odagiKapat();
  });
  addEventListener("popstate", (olay) => {
    const id = olay.state?.odak;
    if (id && odakModeli(VERI, id)) {
      yigin = olay.state.yigin || [id];
      katmaniGoster();
      odakCiz(id, null);
    } else katmaniGizle();
  });
}

function tazelikYazisi(m) {
  if (m.sonGun === null) return "";
  return "✓ " + (m.sonGun === 0 ? "bugün" : `${m.sonGun} gün önce`);
}

function cekmeceIcerigi(model, secilenBag) {
  const { merkez } = model;
  const parca = el("div", "ayrinti");
  const baslik = el("h2", "ayrinti-baslik", merkez.ad);
  baslik.style.color = merkez.renk;
  parca.append(baslik);
  if (merkez.son) {
    const son = el("p", "ayrinti-son", "✓ Son: " + (merkez.son.metin || merkez.son.tarih));
    if (merkez.son.metin) son.title = merkez.son.tarih;
    parca.append(son);
  }
  if (merkez.tur === "proje") {
    parca.append(el("p", "ayrinti-sira", "→ Sıradaki: " + (merkez.sonraki || (merkez.metin ? "—" : "🔒 gizli"))));
  }
  if (merkez.tur !== "proje" && merkez.metin) parca.append(el("p", "ayrinti-metin", merkez.metin));

  parca.append(el("h3", "baslik-kucuk", model.baglar.length ? `Bağlar · ${model.baglar.length}` : "Henüz bağ yok"));
  const sirali = secilenBag
    ? [model.baglar.find((b) => b.id === secilenBag), ...model.baglar.filter((b) => b.id !== secilenBag)]
    : model.baglar;
  const liste = el("ul", "bag-listesi");
  for (const b of sirali) {
    const li = el("li", "bag" + (b.id === secilenBag ? " secili" : ""));
    const isaret = b.tip === "desen" ? "⊘" : b.tip === "acik" ? "·" : b.tahmin ? "┄" : "━";
    const ust = el("button", "bag-ust");
    ust.type = "button";
    ust.append(el("span", "bag-isaret", isaret), el("span", "bag-ad", b.ad));
    ust.style.setProperty("--alan", b.renk);
    ust.setAttribute("aria-label", `${b.ad} öğesine odaklan`);
    ust.onclick = () => odagiAc(b.id);
    li.append(ust);
    if (b.tahmin) li.append(el("span", "bag-etiket", "tahmin"));
    const neden = b.tip === "desen" ? (b.metin || "") : [kisaBaslik(b), b.metin].filter(Boolean).join(" — ");
    if (neden) li.append(el("p", "bag-neden", neden));
    else if (b.tip === "acik") li.append(el("p", "bag-neden soluk", "Notlarda [[bağlantı]] olarak geçiyor."));
    liste.append(li);
  }
  parca.append(liste);
  return parca;
}

function odakCiz(id, secilenBag) {
  const model = odakModeli(VERI, id);
  if (!model) return;
  const { merkez, baglar } = model;
  const sahne = odakKatmani.querySelector(".odak-sahne");
  sahne.replaceChildren();
  odakKatmani.setAttribute("aria-label", merkez.ad + " ve bağları");

  // Sahne ölçüsü: alttaki kısa çekmeceye yer bırak; yatay ve dikey yarıçap ayrı (elips).
  const g = sahne.clientWidth || innerWidth;
  const y = sahne.clientHeight || innerHeight * 0.6;
  const konumlar = halkaKonumlari(baglar.length);
  const enUzak = Math.max(1, ...konumlar.map((k) => Math.hypot(k.x, k.y)));
  const rx = Math.max(60, g / 2 - 56) / enUzak;
  const ry = Math.max(60, y / 2 - 34) / enUzak;
  const ic = konumlar.filter((k) => k.halka === 1).length || 1;
  const etiketGenisligi = Math.max(60, Math.min(112, (2 * Math.PI * rx) / ic - 10));

  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("class", "ipler");
  svg.setAttribute("viewBox", `${-g / 2} ${-y / 2} ${g} ${y}`);
  sahne.append(svg);

  baglar.forEach((b, i) => {
    const x = konumlar[i].x * rx, yy = konumlar[i].y * ry;
    const renk = b.tip === "acik" ? ACIK_IP : ALTIN;
    // görünen ip
    const ip = document.createElementNS(SVG, "line");
    ip.setAttribute("x1", "0"); ip.setAttribute("y1", "0");
    ip.setAttribute("x2", String(x)); ip.setAttribute("y2", String(yy));
    ip.setAttribute("stroke", renk);
    ip.setAttribute("stroke-width", b.tip === "acik" ? "1" : "1.6");
    if (b.tahmin) ip.setAttribute("stroke-dasharray", "4 4");
    ip.setAttribute("class", "ip");
    ip.style.setProperty("--sira", String(i));
    // dokunma alanı (görünmez, kalın)
    const alan = document.createElementNS(SVG, "line");
    alan.setAttribute("x1", "0"); alan.setAttribute("y1", "0");
    alan.setAttribute("x2", String(x)); alan.setAttribute("y2", String(yy));
    alan.setAttribute("class", "ip-dokunma");
    alan.addEventListener("click", () => cekmece.ac(cekmeceIcerigi(model, b.id), { tam: true }));
    svg.append(ip, alan);

    // ipin üstünde kısa başlık: yalnız Claude'un bulduğu bağlarda (desende düğümün adı zaten desen)
    if (b.tip === "gizli" && baglar.length <= ETIKETLI_EN_FAZLA && kisaBaslik(b)) {
      const etiket = el("button", "ip-etiket" + (b.tahmin ? " tahmin" : ""), kisaBaslik(b));
      etiket.type = "button";
      etiket.style.left = `calc(50% + ${x * 0.56}px)`;
      etiket.style.top = `calc(50% + ${yy * 0.56}px)`;
      etiket.onclick = () => cekmece.ac(cekmeceIcerigi(model, b.id), { tam: true });
      sahne.append(etiket);
    }

    // düğüm
    const d = el("button", "dugum");
    d.type = "button";
    d.style.setProperty("--alan", b.renk);
    d.style.setProperty("--x", x + "px");
    d.style.setProperty("--y", yy + "px");
    d.style.setProperty("--sira", String(i));
    d.style.maxWidth = etiketGenisligi + "px";
    d.append(el("span", "dugum-nokta"), el("span", "dugum-ad", b.ad));
    d.onclick = () => odagiAc(b.id);
    sahne.append(d);
  });

  // merkez küre
  const m = el("div", "merkez");
  m.style.setProperty("--alan", merkez.renk);
  m.append(el("span", "halka-dalga"), el("span", "halka-dalga ikinci"));
  const kure = el("button", "kure");
  kure.type = "button";
  kure.append(el("span", "kure-ad", merkez.ad));
  const taze = tazelikYazisi(merkez);
  if (taze) kure.append(el("span", "kure-taze", taze));
  kure.onclick = () => cekmece.ac(cekmeceIcerigi(model, null), { tam: true });
  m.append(kure);
  if (!baglar.length) m.append(el("p", "bag-yok", "Henüz bağ yok"));
  sahne.append(m);

  // açılış: önce merkezde çizilsin (reflow), sonra düğümler yerine kaysın
  sahne.classList.remove("yerlesti");
  void sahne.offsetWidth;
  sahne.classList.add("yerlesti");
  // Yazı tipleri sonradan yüklenirse yazılar büyür; ölçümü onlardan sonra yap.
  const cizim = (sahne.dataset.cizim = String(Number(sahne.dataset.cizim || 0) + 1));
  document.fonts.ready.then(() => { if (sahne.dataset.cizim === cizim) etiketCakismalariniGizle(sahne); });

  cekmece.ac(cekmeceIcerigi(model, secilenBag), { tam: Boolean(secilenBag) });
}

// İp etiketi bir düğüme, küreye ya da başka etikete binerse gizlenir (neden çekmecede okunur).
// Düğümlerin son yeri hesaptan bilinir; animasyonu beklemeden ölçmek için --x/--y kullanılır.
function etiketCakismalariniGizle(sahne) {
  const merkez = sahne.getBoundingClientRect();
  const cx = merkez.left + merkez.width / 2, cy = merkez.top + merkez.height / 2;
  const kutular = [...sahne.querySelectorAll(".dugum")].map((d) => {
    const g = d.offsetWidth, y = d.offsetHeight;
    const x = cx + parseFloat(d.style.getPropertyValue("--x")), yy = cy + parseFloat(d.style.getPropertyValue("--y"));
    return { left: x - g / 2, right: x + g / 2, top: yy - y / 2, bottom: yy + y / 2 };
  });
  kutular.push(sahne.querySelector(".kure").getBoundingClientRect());
  const PAY = 2; // px: yapışık duranlar da çakışmış sayılır
  const kesisir = (a, b) =>
    a.left < b.right + PAY && b.left < a.right + PAY && a.top < b.bottom + PAY && b.top < a.bottom + PAY;
  for (const etiket of sahne.querySelectorAll(".ip-etiket")) {
    const k = etiket.getBoundingClientRect();
    if (kutular.some((b) => kesisir(k, b))) etiket.remove();
    else kutular.push(k);
  }
}

// Bir öğeye dokununca odak açılır ya da odak o öğeye geçer.
export function odagiAc(id) {
  if (!odakKatmani) katmaniKur();
  if (!odakModeli(VERI, id)) return;
  if (odakKatmani.hidden) {
    yigin = [];
    katmaniGoster();
  }
  yigin.push(id);
  history.pushState({ odak: id, yigin: [...yigin] }, "");
  odakCiz(id, null);
}

function katmaniGoster() {
  odakKatmani.hidden = false;
  document.body.classList.add("odakta");
}

function katmaniGizle() {
  if (!odakKatmani) return;
  odakKatmani.hidden = true;
  document.body.classList.remove("odakta");
  cekmece.kapat();
  yigin = [];
}

function odagiKapat() {
  const adim = yigin.length;
  katmaniGizle();
  if (adim) history.go(-adim); // tarayıcı geçmişindeki odak adımlarını da geri al
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
  // Sayfa yenilenince tarayıcı son odak adımını hatırlar; açılışta hep panodan başla.
  if (history.state?.odak) history.replaceState(null, "");
  MODEL = panoModeli(veri);
  document.getElementById("tarih").textContent = MODEL.tarih;
  ciz();
}

