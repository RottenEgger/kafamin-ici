// Odak modeli: bir öğeye dokununca ortada o öğe, etrafında bağları.
// Saf fonksiyonlar (DOM yok); Node'da test edilir.

const VARSAYILAN_RENK = "#8f9bc7";
const ALTIN = "#f4c86a"; // desen (takıldığım yer) rengi

// Bağ sırası: Claude'un emin olduğu gizli bağlar, tahminler, desenler, en son açık [[bağlantılar]].
const sira = (b) => (b.tip === "gizli" ? (b.tahmin ? 1 : 0) : b.tip === "desen" ? 2 : 3);

export function odakModeli(veri, id) {
  const dugumler = veri.dugumler || [];
  const bul = new Map(dugumler.map((d) => [d.id, d]));
  const merkez = bul.get(id);
  if (!merkez) return null;

  const renkler = new Map((veri.alanlar || []).map((a) => [a.ad, a.renk]));
  const renk = (d) => (d.tur === "karadelik" ? ALTIN : renkler.get((d.alan || "").split(" + ")[0]) || VARSAYILAN_RENK);

  const baglar = new Map(); // karşı uç id -> bağ (aynı uca ikinci bağ eklenmez)
  const ekle = (karsi, tip, kayit) => {
    const d = bul.get(karsi);
    if (!d || karsi === id || baglar.has(karsi)) return; // ucu veride yoksa sessizce atla
    baglar.set(karsi, {
      id: d.id, ad: d.ad, tur: d.tur, renk: renk(d), tip,
      tahmin: kayit?.guven === "tahmin",
      baslik: kayit?.baslik || "",
      metin: kayit?.metin || "",
    });
  };

  // Önce gizli bağlar (açıklamaları var), sonra açık bağlar.
  const gizli = [...(veri.gizli || [])].sort((x, y) => (x.guven === "tahmin") - (y.guven === "tahmin"));
  for (const g of gizli) {
    if (g.a !== id && g.b !== id) continue;
    const karsi = g.a === id ? g.b : g.a;
    const desenli = bul.get(karsi)?.tur === "karadelik" || merkez.tur === "karadelik";
    ekle(karsi, desenli ? "desen" : "gizli", g);
  }
  for (const [a, b] of veri.acik || []) {
    if (a === id) ekle(b, "acik", null);
    else if (b === id) ekle(a, "acik", null);
  }

  return {
    merkez: {
      id: merkez.id,
      ad: merkez.ad,
      tur: merkez.tur,
      renk: renk(merkez),
      son: merkez.son ?? null,
      sonGun: merkez.sonGun ?? null,
      sonraki: merkez.sonraki || null,
      metin: merkez.metin || "",
      gizli: !("metin" in merkez), // hassas alan: metin hiç gönderilmez (boş metin değil)
    },
    baglar: [...baglar.values()].sort((x, y) => sira(x) - sira(y) || x.ad.localeCompare(y.ad, "tr")),
  };
}

// Kümede en çok bu kadar bağ çizilir; fazlası çekmecede listelenir.
// (İkinci halka telefonda etiketleri üst üste bindiriyordu.)
export const KUMEDE_EN_FAZLA = 10;

export function gorunenBaglar(baglar, en = KUMEDE_EN_FAZLA) {
  return { gorunen: baglar.slice(0, en), kalan: Math.max(0, baglar.length - en) };
}

// Halka yerleşimi (birim çember koordinatları). İlk nokta tam tepede, saat yönünde eşit aralıklı.
// İç halkaya `ic` kadar öğe sığar; fazlası dış halkalara, her biri yarım adım kaydırılarak gider.
const HALKA_ARASI = 0.6; // dış halkalar arası uzaklık
const EN_AZ_ARALIK = 0.6; // dış halkada iki öğe arası en az yay uzunluğu

export function halkaKonumlari(n, { ic = 10, r1 = 1, r2 = 1.6 } = {}) {
  const sonuc = [];
  let kalan = n;
  let halka = 1;
  while (kalan > 0) {
    const r = halka === 1 ? r1 : r2 + (halka - 2) * HALKA_ARASI;
    const sigan = halka === 1 ? ic : Math.max(1, Math.floor((2 * Math.PI * r) / EN_AZ_ARALIK));
    const adet = Math.min(kalan, sigan);
    const adim = (2 * Math.PI) / adet;
    const kayma = halka === 1 ? 0 : adim / 2;
    for (let i = 0; i < adet; i++) {
      const aci = -Math.PI / 2 + kayma + i * adim;
      sonuc.push({ x: r * Math.cos(aci), y: r * Math.sin(aci), halka });
    }
    kalan -= adet;
    halka += 1;
  }
  return sonuc;
}
