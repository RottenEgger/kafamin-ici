// Düz JSON'u parolayla şifreler: {v, salt, iv, veri} (base64).
// Kullanım: parola stdin'den gelir (Anahtar Zinciri'nden borulanır)
//   security find-generic-password -s kafamin-ici -w | node araclar/sifrele.mjs duz.json cikti.json salt.txt
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { anahtarTuret, b64Yaz, b64Oku } from "../docs/kilit.js";

export async function sifrele(duzMetin, parola, saltB64) {
  const anahtar = await anahtarTuret(parola, saltB64);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const sifreli = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv }, anahtar, new TextEncoder().encode(duzMetin));
  return { v: 1, salt: saltB64, iv: b64Yaz(iv), veri: b64Yaz(new Uint8Array(sifreli)) };
}

// Salt dosyası yoksa 16 rastgele bayt üretip yazar; varsa okur
function saltAl(yol) {
  if (existsSync(yol)) {
    const salt = readFileSync(yol, "utf8").trim();
    let uzunluk = -1;
    try { uzunluk = b64Oku(salt).length; } catch { /* geçersiz base64 */ }
    if (uzunluk !== 16) {
      throw new Error(`salt dosyası geçersiz (${yol}): tam 16 bayt olmalı. Dosyayı elle düzeltmeyin; silip yeniden üretin.`);
    }
    return salt;
  }
  const salt = b64Yaz(crypto.getRandomValues(new Uint8Array(16)));
  mkdirSync(dirname(yol), { recursive: true });
  writeFileSync(yol, salt + "\n");
  return salt;
}

async function stdinOku() {
  const parcalar = [];
  for await (const p of process.stdin) parcalar.push(p);
  return Buffer.concat(parcalar).toString("utf8");
}

async function main() {
  const [duzYol, ciktiYol, saltYol] = process.argv.slice(2);
  if (!duzYol || !ciktiYol || !saltYol) {
    console.error("Kullanım: node araclar/sifrele.mjs <duz.json> <cikti.json> <salt.txt>  (parola stdin'den)");
    process.exit(2);
  }
  // Yalnız tek bir sondaki satır sonunu at (\n ya da \r\n)
  const parola = (await stdinOku()).replace(/\r?\n$/, "");
  if (parola === "") {
    console.error("Hata: parola boş. Parolayı stdin'den verin.");
    process.exit(1);
  }
  const kapsul = await sifrele(readFileSync(duzYol, "utf8"), parola, saltAl(saltYol));
  writeFileSync(ciktiYol, JSON.stringify(kapsul));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch((e) => {
    console.error("Hata:", e.message);
    process.exit(1);
  });
}
