// Pano modeli: çözülmüş veriyi (uret.py çıktısı) panonun satırlarına çevirir.
// Saf fonksiyonlar: sayfaya (DOM'a) dokunmaz, bu yüzden Node'da test edilebilir.

const VARSAYILAN_RENK = "#8f9bc7";
const SON_ALAN = "Hayat"; // her zaman en altta
const SATIRDA_EN_FAZLA_IS = 2; // proje satırının altında görünen yapılacak sayısı
const CALISILAN_GUN = 7; // "son 7 gün"

// Tazelik: bugün çalışıldıysa 1, 9 gün ve öncesi 0.25, arası doğrusal; bilinmiyorsa 0.
export function tazelik(sonGun) {
  if (sonGun === null || sonGun === undefined) return 0;
  if (sonGun >= 9) return 0.25;
  return 1 - (0.75 * sonGun) / 9;
}

// "Kod + Okul" -> ["Kod", "Okul"]
const alanAdlari = (d) => (d.alan || "").split(" + ").filter(Boolean);
const hassasMi = (d) => !("metin" in d); // hassas alanda metin hiç gönderilmez
const siraAd = (a, b) => a.localeCompare(b, "tr");
// Bilinmeyen gün sayısı en sona gitsin diye sonsuz sayılır.
const gunSirasi = (g) => (g === null || g === undefined ? Infinity : g);

function isYap(d) {
  return { id: d.id, ad: d.ad, bekliyorGun: d.bekliyorGun ?? null, unutulmus: Boolean(d.unutulmus) };
}

export function panoModeli(veri) {
  const dugumler = veri.dugumler || [];
  const renkler = new Map((veri.alanlar || []).map((a) => [a.ad, a.renk]));
  const renk = (ad) => renkler.get(ad) || VARSAYILAN_RENK;
  const bul = new Map(dugumler.map((d) => [d.id, d]));

  // Bir düğümün komşuları, bağ türüne göre (veri sırası korunur).
  const komsu = (id, ciftler) => ciftler.filter(([a, b]) => a === id || b === id).map(([a, b]) => (a === id ? b : a));
  const acik = veri.acik || [];
  const gizliCift = (veri.gizli || []).map((g) => [g.a, g.b]);

  const projeler = dugumler.filter((d) => d.tur === "proje" && d.durum !== "arsiv");
  const projeIdleri = new Set(projeler.map((p) => p.id));

  // Her açık yapılacak, açık çiftlerde ilk eşleştiği projeye aittir.
  const isinProjesi = new Map();
  for (const d of dugumler) {
    if (d.tur !== "gorev" || d.durum !== "bekliyor") continue;
    const p = komsu(d.id, acik).find((k) => projeIdleri.has(k));
    if (p) isinProjesi.set(d.id, p);
  }

  // Satırdaki fikir: önce açık bağ, yoksa gizli bağ.
  const satirdakiFikirler = new Set();
  const fikirBul = (pid) => {
    const fikirMi = (k) => bul.get(k)?.tur === "fikir";
    const f = komsu(pid, acik).find(fikirMi) ?? komsu(pid, gizliCift).find(fikirMi);
    if (!f) return null;
    satirdakiFikirler.add(f);
    return { id: f, ad: bul.get(f).ad };
  };

  const satirlar = projeler.map((p) => {
    const [birinci, ikinci] = alanAdlari(p);
    const isler = dugumler.filter((d) => isinProjesi.get(d.id) === p.id).map(isYap);
    const sonGun = p.sonGun ?? null;
    return {
      alan: birinci || SON_ALAN,
      satir: {
        id: p.id,
        ad: p.ad,
        renk: renk(birinci),
        renk2: ikinci ? renk(ikinci) : null,
        son: p.son ?? null,
        sonGun,
        tazelik: tazelik(sonGun),
        sonraki: hassasMi(p) ? null : p.sonraki || null,
        gizli: hassasMi(p),
        fikir: fikirBul(p.id),
        yapilacaklar: isler.slice(0, SATIRDA_EN_FAZLA_IS),
        fazla: Math.max(0, isler.length - SATIRDA_EN_FAZLA_IS),
      },
    };
  });

  // Alanlara dağıt.
  const alanlar = new Map();
  const alanAl = (ad) => {
    if (!alanlar.has(ad)) alanlar.set(ad, { ad, renk: renk(ad), projeler: [], yapilacaklar: [], yapilanlar: [], cipler: [] });
    return alanlar.get(ad);
  };
  for (const { alan, satir } of satirlar) alanAl(alan).projeler.push(satir);
  for (const d of dugumler) {
    const ad = alanAdlari(d)[0] || SON_ALAN;
    if (d.tur === "gorev" && d.durum === "bekliyor" && !isinProjesi.has(d.id)) alanAl(ad).yapilacaklar.push(isYap(d));
    else if (d.tur === "gorev" && d.durum === "bitti") alanAl(ad).yapilanlar.push(isYap(d));
    else if (["fikir", "ders", "kaynak"].includes(d.tur) && !satirdakiFikirler.has(d.id))
      alanAl(ad).cipler.push({ id: d.id, ad: d.ad, tur: d.tur });
  }

  // Sıralama: alan içinde en taze proje üstte; alanlar en taze projelerine göre, Hayat en sonda.
  for (const a of alanlar.values()) {
    a.projeler.sort((x, y) => gunSirasi(x.sonGun) - gunSirasi(y.sonGun) || siraAd(x.ad, y.ad));
  }
  const enTaze = (a) => Math.min(Infinity, ...a.projeler.map((p) => gunSirasi(p.sonGun)));
  const siraliAlanlar = [...alanlar.values()].sort(
    (x, y) => (x.ad === SON_ALAN) - (y.ad === SON_ALAN) || enTaze(x) - enTaze(y) || siraAd(x.ad, y.ad),
  );

  const bekleyenler = dugumler.filter((d) => d.tur === "gorev" && d.durum === "bekliyor");
  const gunler = bekleyenler.map((d) => d.bekliyorGun).filter((g) => typeof g === "number");
  const tumSatirlar = satirlar.map((s) => s.satir);

  return {
    tarih: veri.tarih || "",
    ozet: {
      calisilan: tumSatirlar.filter((s) => s.sonGun !== null && s.sonGun < CALISILAN_GUN).length,
      siradaki: tumSatirlar.filter((s) => s.sonraki).length,
      bekleyen: bekleyenler.length,
      enEskiGun: gunler.length ? Math.max(...gunler) : null,
    },
    desenler: dugumler
      .filter((d) => d.tur === "karadelik")
      .map((d) => ({ id: d.id, ad: d.ad, uyeSayisi: (veri.gizli || []).filter((g) => g.a === d.id).length }))
      .sort((x, y) => y.uyeSayisi - x.uyeSayisi || siraAd(x.ad, y.ad)),
    alanlar: siraliAlanlar,
  };
}

// Özet kutusuna dokununca pano süzülür: "hepsi", "calisilan" ya da "bekleyen".
export function suz(model, secim) {
  if (secim === "hepsi") return model;
  const alanlar = model.alanlar
    .map((a) => {
      if (secim === "calisilan") {
        const projeler = a.projeler.filter((p) => p.sonGun !== null && p.sonGun < CALISILAN_GUN);
        return { ...a, projeler, yapilacaklar: [], yapilanlar: [], cipler: [] };
      }
      const projeler = a.projeler.filter((p) => p.yapilacaklar.length > 0);
      return { ...a, projeler, yapilanlar: [], cipler: [] };
    })
    .filter((a) => a.projeler.length || a.yapilacaklar.length);
  return { ...model, alanlar };
}
