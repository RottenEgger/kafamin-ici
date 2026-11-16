import { test } from "node:test";
import assert from "node:assert/strict";
import { sifrele } from "../araclar/sifrele.mjs";
import { anahtarTuret, coz } from "../docs/kilit.js";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync, readFileSync, existsSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const CLI = fileURLToPath(new URL("../araclar/sifrele.mjs", import.meta.url));

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

test("NFD ve NFC biçimli parola aynı anahtarı verir", async () => {
  const nfc = "Kâğıt ışık".normalize("NFC");
  const nfd = "Kâğıt ışık".normalize("NFD");
  assert.notEqual(nfc, nfd);
  const kapsul = await sifrele(JSON.stringify(VERI), nfd, SALT);
  assert.deepEqual(await coz(kapsul, await anahtarTuret(nfc, SALT)), VERI);
  const kapsul2 = await sifrele(JSON.stringify(VERI), nfc, SALT);
  assert.deepEqual(await coz(kapsul2, await anahtarTuret(nfd, SALT)), VERI);
});

test("16 bayt olmayan salt dosyasında CLI hata verir", () => {
  const klasor = mkdtempSync(join(tmpdir(), "sifre-"));
  try {
    writeFileSync(join(klasor, "duz.json"), "{}");
    writeFileSync(join(klasor, "salt.txt"), Buffer.alloc(3, 1).toString("base64") + "\n");
    const s = spawnSync("node", [CLI, join(klasor, "duz.json"), join(klasor, "cikti.json"), join(klasor, "salt.txt")],
      { input: "parola\n", encoding: "utf8" });
    assert.notEqual(s.status, 0);
    assert.match(s.stderr, /salt/i);
    assert.equal(existsSync(join(klasor, "cikti.json")), false);
  } finally {
    rmSync(klasor, { recursive: true, force: true });
  }
});

function cliyleSifrele(girdi) {
  const klasor = mkdtempSync(join(tmpdir(), "sifre-"));
  try {
    writeFileSync(join(klasor, "duz.json"), JSON.stringify(VERI));
    const s = spawnSync("node", [CLI, join(klasor, "duz.json"), join(klasor, "cikti.json"), join(klasor, "salt.txt")],
      { input: girdi, encoding: "utf8" });
    assert.equal(s.status, 0, s.stderr);
    const kapsul = JSON.parse(readFileSync(join(klasor, "cikti.json"), "utf8"));
    const salt = kapsul.salt;
    return { kapsul, salt };
  } finally {
    rmSync(klasor, { recursive: true, force: true });
  }
}

test("Anahtar Zinciri hex çıktısı CLI'da çözülür, düz parolayla açılır", async () => {
  const parola = "Kâğıt ışık 2026";
  const hex = Buffer.from(parola, "utf8").toString("hex");
  const { kapsul, salt } = cliyleSifrele(hex + "\n");
  assert.deepEqual(await coz(kapsul, await anahtarTuret(parola, salt)), VERI);
});

test("hex görünen ASCII parola çözülmez", async () => {
  const { kapsul, salt } = cliyleSifrele("deadbeef\n");
  assert.deepEqual(await coz(kapsul, await anahtarTuret("deadbeef", salt)), VERI);
});
