// Kilit: parolayı anahtara çevirir, şifreli kapsülü çözer.
// Tarayıcıda ve Node'da aynı kod çalışır (yalnız globalThis.crypto.subtle).

export const TUR = 600000; // PBKDF2 turu
const DB_AD = "kafamin-ici";
const DEPO = "anahtar";
const ANAHTAR_ADI = "ana";

// Bayt dizisi <-> base64 (Buffer yok; büyük dizilerde yığın taşmasın diye parça parça)
export function b64Yaz(bayt) {
  let s = "";
  for (let i = 0; i < bayt.length; i += 0x8000) {
    s += String.fromCharCode(...bayt.subarray(i, i + 0x8000));
  }
  return btoa(s);
}

export function b64Oku(metin) {
  const s = atob(metin);
  const bayt = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) bayt[i] = s.charCodeAt(i);
  return bayt;
}

// Paroladan AES-GCM-256 anahtarı; dışarı çıkarılamaz (extractable: false)
export async function anahtarTuret(parola, saltB64) {
  const subtle = globalThis.crypto.subtle;
  const ham = await subtle.importKey(
    "raw", new TextEncoder().encode(parola), "PBKDF2", false, ["deriveKey"]);
  return subtle.deriveKey(
    { name: "PBKDF2", hash: "SHA-256", salt: b64Oku(saltB64), iterations: TUR },
    ham,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]);
}

// Kapsülü çözer; anahtar yanlışsa ya da veri bozuksa fırlatır
export async function coz(kapsul, anahtar) {
  const duz = await globalThis.crypto.subtle.decrypt(
    { name: "AES-GCM", iv: b64Oku(kapsul.iv) }, anahtar, b64Oku(kapsul.veri));
  return JSON.parse(new TextDecoder().decode(duz));
}

// --- IndexedDB (yalnız tarayıcı) ---
function dbAc() {
  return new Promise((coz_, red) => {
    const istek = indexedDB.open(DB_AD, 1);
    istek.onupgradeneeded = () => istek.result.createObjectStore(DEPO);
    istek.onsuccess = () => coz_(istek.result);
    istek.onerror = () => red(istek.error);
  });
}

async function islem(mod, calistir) {
  const db = await dbAc();
  try {
    return await new Promise((coz_, red) => {
      const tx = db.transaction(DEPO, mod);
      const istek = calistir(tx.objectStore(DEPO));
      tx.oncomplete = () => coz_(istek.result);
      tx.onerror = () => red(tx.error);
      tx.onabort = () => red(tx.error);
    });
  } finally {
    db.close();
  }
}

export const anahtarSakla = (anahtar) => islem("readwrite", (d) => d.put(anahtar, ANAHTAR_ADI));
export const anahtarGetir = async () => (await islem("readonly", (d) => d.get(ANAHTAR_ADI))) ?? null;
export const anahtarSil = () => islem("readwrite", (d) => d.delete(ANAHTAR_ADI));
