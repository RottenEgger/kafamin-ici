#!/bin/bash
# Veriyi üretir, şifreler ve GitHub'a gönderir. Veri değişmediyse hiçbir şey yapmaz.
# Test için: PAROLA_KOMUTU parolayı okuyan komutu, GONDER=0 ise "git push"u atlar.
set -euo pipefail
cd "$(dirname "$0")/.."

KASA="${KASA:-$HOME/Desktop/İkinci Beyin}"
PAROLA_KOMUTU="${PAROLA_KOMUTU:-security find-generic-password -s kafamin-ici -w}"
GONDER="${GONDER:-1}"

mkdir -p .yerel docs

# 1) Kasadan düz veriyi üret (yalnızca bu bilgisayarda kalır).
python3 -I araclar/uret.py "$KASA" .yerel/veri.json

# 2) Özet aynıysa çık.
YENI="$(shasum -a 256 .yerel/veri.json | cut -d' ' -f1)"
ESKI="$(cat .yerel/ozet.txt 2>/dev/null || true)"
if [ "$YENI" = "$ESKI" ] && [ -f docs/veri.sifreli.json ]; then
  echo "Değişiklik yok, gönderilmedi."
  exit 0
fi

# 3) Parolayı komuttan oku (ekrana yazılmaz) ve şifrele.
$PAROLA_KOMUTU | node araclar/sifrele.mjs .yerel/veri.json docs/veri.sifreli.json .yerel/salt.txt
echo "$YENI" > .yerel/ozet.txt

# 4) Yalnızca şifreli dosya kaydedilir ve gönderilir.
git add docs/veri.sifreli.json
if git diff --cached --quiet -- docs/veri.sifreli.json; then
  echo "Değişiklik yok."
  exit 0
fi
git commit -q -m "Veri güncellendi" -- docs/veri.sifreli.json
if [ "$GONDER" = "1" ]; then
  git push -q origin main
  echo "Veri güncellendi ve GitHub'a gönderildi."
else
  echo "Veri güncellendi (GONDER=0: gönderilmedi)."
fi
