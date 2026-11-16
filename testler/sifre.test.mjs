import { test } from "node:test";
import assert from "node:assert/strict";
import { sifrele } from "../araclar/sifrele.mjs";
import { anahtarTuret, coz } from "../docs/kilit.js";

const SALT = Buffer.alloc(16, 7).toString("base64");
const VERI = { tarih: "16 Kasım 2026", alanlar: [{ ad: "Örnek", x: 1.5 }] };

test("gidiş-dönüş: şifrele sonra çöz aynı nesneyi verir", async () => {
  const kapsul = await sifrele(JSON.stringify(VERI), "deneme parolası", SALT);
  assert.equal(kapsul.v, 1);
  assert.equal(kapsul.salt, SALT);
  const anahtar = await anahtarTuret("deneme parolası", SALT);
  assert.deepEqual(await coz(kapsul, anahtar), VERI);
});

test("yanlış parola fırlatır", async () => {
  const kapsul = await sifrele(JSON.stringify(VERI), "doğru", SALT);
  const yanlis = await anahtarTuret("yanlış", SALT);
  await assert.rejects(() => coz(kapsul, yanlis));
});

test("iv her seferinde farklı, salt aynı", async () => {
  const a = await sifrele("{}", "p", SALT);
  const b = await sifrele("{}", "p", SALT);
  assert.notEqual(a.iv, b.iv);
  assert.equal(a.salt, b.salt);
  assert.equal(Buffer.from(a.iv, "base64").length, 12);
});

test("parola Türkçe karakterli", async () => {
  const parola = "Kâğıt ışık 2026 şiir";
  const kapsul = await sifrele(JSON.stringify(VERI), parola, SALT);
  const anahtar = await anahtarTuret(parola, SALT);
  assert.deepEqual(await coz(kapsul, anahtar), VERI);
});

test("anahtar dışarı çıkarılamaz", async () => {
  const anahtar = await anahtarTuret("p", SALT);
  assert.equal(anahtar.extractable, false);
  await assert.rejects(() => crypto.subtle.exportKey("raw", anahtar));
});
