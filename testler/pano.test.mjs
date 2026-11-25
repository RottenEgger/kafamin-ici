// Pano modeli testleri: çözülmüş veriden pano satırlarına (docs/pano.js).
// Örnek veri uydurmadır; gerçek not adı kullanılmaz.
import { test } from "node:test";
import assert from "node:assert/strict";
import { panoModeli, suz, tazelik } from "../docs/pano.js";

const ORNEK_VERI = {
  tarih: "16 Kasım 2026",
  alanlar: [
    { ad: "Hayat", renk: "#7dffb2" },
    { ad: "Kod", renk: "#5fd4ff" },
    { ad: "Okul", renk: "#ff9f7a" },
    { ad: "Para", renk: "#9dffea" },
  ],
  dugumler: [
    { id: "Robot", ad: "Robot", tur: "proje", durum: "bitti", alan: "Kod", metin: "m", sonraki: "Pili tak", son: { tarih: "2026-11-16", metin: "Motor döndü" }, sonGun: 0 },
    { id: "Site", ad: "Site", tur: "proje", durum: "surekli", alan: "Kod + Okul", metin: "m", sonraki: "Yayınla", son: { tarih: "2026-11-13", metin: "Tasarım bitti" }, sonGun: 3 },
    { id: "Bahçe", ad: "Bahçe", tur: "proje", durum: "surekli", alan: "Hayat", metin: "m", sonraki: "Fide dik", son: { tarih: "2026-11-15", metin: "Saksı alındı" }, sonGun: 1 },
    { id: "Sınıf", ad: "Sınıf", tur: "proje", durum: "surekli", alan: "Okul", metin: "m", sonraki: "Notları gir", son: { tarih: "2026-11-14", metin: "Liste hazır" }, sonGun: 2 },
    { id: "Eski", ad: "Eski", tur: "proje", durum: "arsiv", alan: "Kod", metin: "m" },
    { id: "Yeni İş", ad: "Yeni İş", tur: "proje", durum: "surekli", alan: "Okul", metin: "m", sonraki: "Başla" },
    { id: "Birikim", ad: "Birikim", tur: "proje", durum: "surekli", alan: "Para", son: { tarih: "2026-11-11" }, sonGun: 5 },
    { id: "Uçan Robot", ad: "Uçan Robot", tur: "fikir", durum: "bekliyor", alan: "Kod", metin: "" },
    { id: "Ayçiçeği", ad: "Ayçiçeği", tur: "fikir", durum: "bekliyor", alan: "Okul", metin: "" },
    { id: "Matematik", ad: "Matematik", tur: "ders", durum: "surekli", alan: "Okul", metin: "" },
    { id: "Yeni Kaynak", ad: "Yeni Kaynak", tur: "kaynak", durum: "surekli", alan: "Hayat", metin: "" },
    { id: "gorev:pil al", ad: "Pil al", tur: "gorev", durum: "bekliyor", alan: "Kod", metin: "Pil al", bekliyorGun: 2 },
    { id: "gorev:vida al", ad: "Vida al", tur: "gorev", durum: "bekliyor", alan: "Kod", metin: "Vida al", bekliyorGun: 1 },
    { id: "gorev:lehim", ad: "Lehim", tur: "gorev", durum: "bekliyor", alan: "Kod", metin: "Lehim", bekliyorGun: 0 },
    { id: "gorev:fatura öde", ad: "Fatura öde", tur: "gorev", durum: "bekliyor", alan: "Hayat", metin: "Fatura öde", bekliyorGun: 20, unutulmus: true },
    { id: "gorev:kitabı bitir", ad: "Kitabı bitir", tur: "gorev", durum: "bitti", alan: "Hayat", metin: "Kitabı bitir" },
    { id: "desen:Karar", ad: "Karar", tur: "karadelik", durum: "bekliyor", alan: "Desen", metin: "Aynı karar." },
  ],
  acik: [
    ["Robot", "Uçan Robot"],
    ["Robot", "gorev:lehim"],
    ["Robot", "gorev:pil al"],
    ["Robot", "gorev:vida al"],
  ],
  gizli: [
    { a: "desen:Karar", b: "Robot", baslik: "Kara deliğe çekilen: Robot", metin: "", guven: "emin" },
    { a: "desen:Karar", b: "Site", baslik: "Kara deliğe çekilen: Site", metin: "", guven: "emin" },
    { a: "Ayçiçeği", b: "Sınıf", baslik: "Okulda dikim", metin: "", guven: "tahmin" },
  ],
  buHafta: [],
};

const model = () => panoModeli(ORNEK_VERI);
const alan = (m, ad) => m.alanlar.find((a) => a.ad === ad);
const satir = (m, id) => m.alanlar.flatMap((a) => a.projeler).find((p) => p.id === id);

test("tazelik: bugün 1, 3 gün 0.75, 9+ gün 0.25, bilinmiyor 0", () => {
  assert.equal(tazelik(0), 1);
  assert.equal(tazelik(3), 0.75);
  assert.equal(tazelik(9), 0.25);
  assert.equal(tazelik(20), 0.25);
  assert.equal(tazelik(null), 0);
  assert.equal(tazelik(undefined), 0);
});

test("alan sırası en tazeden, Hayat her zaman en sonda", () => {
  assert.deepEqual(model().alanlar.map((a) => a.ad), ["Kod", "Okul", "Para", "Hayat"]);
});

test("arşivdeki proje görünmez", () => {
  assert.equal(satir(model(), "Eski"), undefined);
});

test("projeler tazelikten, son satırı olmayan en sonda", () => {
  assert.deepEqual(alan(model(), "Okul").projeler.map((p) => p.id), ["Sınıf", "Yeni İş"]);
  const yeni = satir(model(), "Yeni İş");
  assert.equal(yeni.son, null);
  assert.equal(yeni.sonGun, null);
  assert.equal(yeni.tazelik, 0);
});

test("iki alanlı projeye ikinci renk şeridi", () => {
  const site = satir(model(), "Site");
  assert.equal(site.renk, "#5fd4ff");
  assert.equal(site.renk2, "#ff9f7a");
  assert.equal(satir(model(), "Robot").renk2, null);
});

test("yapılacak açık çiftle projeye bağlanır: en çok 2 görünür, kalanı fazla", () => {
  const robot = satir(model(), "Robot");
  assert.equal(robot.yapilacaklar.length, 2);
  assert.equal(robot.fazla, 1);
  assert.deepEqual(alan(model(), "Kod").yapilacaklar, []);
});

test("projesiz yapılacak ve yapılan alanının listesine düşer", () => {
  const hayat = alan(model(), "Hayat");
  assert.deepEqual(hayat.yapilacaklar, [{ id: "gorev:fatura öde", ad: "Fatura öde", bekliyorGun: 20, unutulmus: true }]);
  assert.deepEqual(hayat.yapilanlar.map((i) => i.id), ["gorev:kitabı bitir"]);
});

test("hassas proje: gizli, sıradakisiz, son metinsiz", () => {
  const b = satir(model(), "Birikim");
  assert.equal(b.gizli, true);
  assert.equal(b.sonraki, null);
  assert.deepEqual(b.son, { tarih: "2026-11-11" });
});

test("fikir açık çiftten satıra gelir ve çiplerde tekrar etmez", () => {
  assert.deepEqual(satir(model(), "Robot").fikir, { id: "Uçan Robot", ad: "Uçan Robot" });
  assert.ok(!alan(model(), "Kod").cipler.some((c) => c.id === "Uçan Robot"));
});

test("açık çift yoksa fikir gizli bağdan gelir", () => {
  assert.deepEqual(satir(model(), "Sınıf").fikir, { id: "Ayçiçeği", ad: "Ayçiçeği" });
  assert.ok(!alan(model(), "Okul").cipler.some((c) => c.id === "Ayçiçeği"));
});

test("bağlanmamış ders ve kaynak alan çiplerinde", () => {
  assert.deepEqual(alan(model(), "Okul").cipler, [{ id: "Matematik", ad: "Matematik", tur: "ders" }]);
  assert.deepEqual(alan(model(), "Hayat").cipler, [{ id: "Yeni Kaynak", ad: "Yeni Kaynak", tur: "kaynak" }]);
});

test("özet sayıları", () => {
  assert.deepEqual(model().ozet, { calisilan: 5, siradaki: 5, bekleyen: 4, enEskiGun: 20 });
});

test("desenler üye sayısıyla", () => {
  assert.deepEqual(model().desenler, [{ id: "desen:Karar", ad: "Karar", uyeSayisi: 2 }]);
});

test("boş veri çökmez", () => {
  const bos = panoModeli({ tarih: "", alanlar: [], dugumler: [], acik: [], gizli: [] });
  assert.deepEqual(bos.alanlar, []);
  assert.deepEqual(bos.ozet, { calisilan: 0, siradaki: 0, bekleyen: 0, enEskiGun: null });
});

test("suz: hepsi aynı modeli verir", () => {
  const m = model();
  assert.deepEqual(suz(m, "hepsi"), m);
});

test("suz: çalışılan yalnız son 7 günde günlüğü olan satırlar", () => {
  const m = suz(model(), "calisilan");
  assert.deepEqual(m.alanlar.map((a) => a.ad), ["Kod", "Okul", "Para", "Hayat"]);
  assert.deepEqual(alan(m, "Okul").projeler.map((p) => p.id), ["Sınıf"]);
  assert.deepEqual(alan(m, "Hayat").yapilacaklar, []);
});

test("suz: bekleyen yalnız yapılacağı olan satırlar ve listeler; boş alan düşer", () => {
  const m = suz(model(), "bekleyen");
  assert.deepEqual(m.alanlar.map((a) => a.ad), ["Kod", "Hayat"]);
  assert.deepEqual(alan(m, "Kod").projeler.map((p) => p.id), ["Robot"]);
  assert.equal(alan(m, "Hayat").yapilacaklar.length, 1);
  assert.deepEqual(alan(m, "Hayat").cipler, []);
});
