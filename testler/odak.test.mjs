// Odak modeli testleri: bir öğenin bağları ve halka yerleşimi (docs/odak.js).
// Örnek veri uydurmadır.
import { test } from "node:test";
import assert from "node:assert/strict";
import { odakModeli, halkaKonumlari } from "../docs/odak.js";

const V = {
  alanlar: [
    { ad: "Kod", renk: "#5fd4ff" },
    { ad: "Okul", renk: "#ff9f7a" },
  ],
  dugumler: [
    { id: "A", ad: "Robot", tur: "proje", durum: "surekli", alan: "Kod", metin: "Amaç", sonraki: "Pili tak", son: { tarih: "2026-11-16", metin: "Motor döndü" }, sonGun: 0 },
    { id: "B", ad: "Site", tur: "proje", durum: "surekli", alan: "Okul + Kod", metin: "" },
    { id: "C", ad: "Uçan", tur: "fikir", durum: "bekliyor", alan: "Kod", metin: "" },
    { id: "D", ad: "Matematik", tur: "ders", durum: "surekli", alan: "Okul", metin: "" },
    { id: "Yalnız", ad: "Yalnız", tur: "proje", durum: "surekli", alan: "Hayat" },
    { id: "desen:X", ad: "X", tur: "karadelik", durum: "bekliyor", alan: "Desen", metin: "Ortak tıkanma" },
  ],
  acik: [["A", "B"], ["A", "D"]],
  gizli: [
    { a: "A", b: "B", baslik: "İki iş", metin: "neden bir", guven: "emin" },
    { a: "C", b: "A", baslik: "Belki", metin: "neden iki", guven: "tahmin" },
    { a: "desen:X", b: "A", baslik: "Kara deliğe çekilen: Robot", metin: "Ortak tıkanma", guven: "emin" },
    { a: "desen:X", b: "B", baslik: "Kara deliğe çekilen: Site", metin: "Ortak tıkanma", guven: "emin" },
    { a: "A", b: "Hayalet", baslik: "Yok", metin: "", guven: "emin" },
  ],
};

test("bilinmeyen id → null", () => {
  assert.equal(odakModeli(V, "Olmayan"), null);
});

test("merkez alanları", () => {
  assert.deepEqual(odakModeli(V, "A").merkez, {
    id: "A", ad: "Robot", tur: "proje", renk: "#5fd4ff",
    son: { tarih: "2026-11-16", metin: "Motor döndü" }, sonGun: 0, sonraki: "Pili tak", metin: "Amaç",
  });
});

test("bağ sırası: gizli emin, gizli tahmin, desen, açık; eksik uç atlanır", () => {
  const b = odakModeli(V, "A").baglar;
  assert.deepEqual(b.map((x) => [x.id, x.tip, x.tahmin]), [
    ["B", "gizli", false],
    ["C", "gizli", true],
    ["desen:X", "desen", false],
    ["D", "acik", false],
  ]);
});

test("aynı uca açık ve gizli bağ → yalnız gizli, açıklamasıyla", () => {
  const b = odakModeli(V, "A").baglar.filter((x) => x.id === "B");
  assert.equal(b.length, 1);
  assert.equal(b[0].baslik, "İki iş");
  assert.equal(b[0].metin, "neden bir");
  assert.equal(b[0].renk, "#ff9f7a");
});

test("açık bağın başlığı ve metni boş", () => {
  const d = odakModeli(V, "A").baglar.find((x) => x.id === "D");
  assert.equal(d.baslik, "");
  assert.equal(d.metin, "");
});

test("desen merkezi üyelerini verir, renk altın", () => {
  const m = odakModeli(V, "desen:X");
  assert.equal(m.merkez.renk, "#f4c86a");
  assert.deepEqual(m.baglar.map((x) => [x.id, x.tip]), [["A", "desen"], ["B", "desen"]]);
});

test("bağsız öğe: boş liste, hassas merkezde metin boş", () => {
  const m = odakModeli(V, "Yalnız");
  assert.deepEqual(m.baglar, []);
  assert.equal(m.merkez.metin, "");
  assert.equal(m.merkez.sonraki, null);
  assert.equal(m.merkez.son, null);
});

test("halka: 0 öğe → boş", () => {
  assert.deepEqual(halkaKonumlari(0), []);
});

test("halka: ilk nokta tepede, saat yönünde", () => {
  const p = halkaKonumlari(4);
  assert.ok(Math.abs(p[0].x) < 1e-9 && Math.abs(p[0].y + 1) < 1e-9);
  assert.ok(Math.abs(p[1].x - 1) < 1e-9 && Math.abs(p[1].y) < 1e-9); // sağ
  assert.ok(p.every((n) => n.halka === 1));
});

test("halka: 13 öğe → 10 iç, 3 dış (yarıçap 1.6)", () => {
  const p = halkaKonumlari(13);
  assert.equal(p.filter((n) => n.halka === 1).length, 10);
  const dis = p.filter((n) => n.halka === 2);
  assert.equal(dis.length, 3);
  for (const n of dis) assert.ok(Math.abs(Math.hypot(n.x, n.y) - 1.6) < 1e-9);
});

test("halka: 1..24 öğede hiçbir iki nokta 0.5'ten yakın değil", () => {
  for (let n = 1; n <= 24; n++) {
    const p = halkaKonumlari(n);
    for (let i = 0; i < p.length; i++)
      for (let j = i + 1; j < p.length; j++)
        assert.ok(Math.hypot(p[i].x - p[j].x, p[i].y - p[j].y) >= 0.5, `n=${n} i=${i} j=${j}`);
  }
});
