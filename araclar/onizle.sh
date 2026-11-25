#!/bin/bash
# Yerel önizleme: sayfayı DENEME parolasıyla (onizleme) .yerel/onizleme/ içine kurar.
# Hiçbir şey yayınlamaz; docs/veri.sifreli.json'a, Anahtar Zinciri'ne ve .yerel/alanlar.json'a dokunmaz.
#
# Kullanım:
#   bash araclar/onizle.sh            -> testteki uydurma kasayla (testler/ornek_kasa)
#   bash araclar/onizle.sh --gercek   -> gerçek kasadan, bu daldaki kodla (yalnız bu Mac'te kalır)
# Sonra: python3 -m http.server 8001 -d .yerel/onizleme  ve tarayıcıda http://localhost:8001
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")/.."

HEDEF=".yerel/onizleme"
mkdir -p .yerel
rm -rf "$HEDEF"
cp -R docs "$HEDEF"
rm -f "$HEDEF/veri.sifreli.json" "$HEDEF/CNAME"

DUZ=".yerel/onizleme-veri.json"
if [ "${1:-}" = "--gercek" ]; then
  KASA="${KASA:-$HOME/Desktop/İkinci Beyin}"
  # Alan renkleri için gerçek tablonun KOPYASI kullanılır; asıl tablo değişmez.
  ANA_TABLO="${KAFAM_TABLO:-$HOME/Desktop/KafaminIci/.yerel/alanlar.json}"
  TABLO=".yerel/onizleme-alanlar.json"
  if [ -f "$ANA_TABLO" ]; then cp "$ANA_TABLO" "$TABLO"; else rm -f "$TABLO"; fi
else
  KASA="${KASA:-testler/ornek_kasa}"  # deneme için başka bir uydurma kasa verilebilir
  TABLO=""
fi
# uret.uret_uyarili doğrudan çağrılır: gerçek alan tablosu (.yerel/alanlar.json) değişmesin.
python3 -I -c '
import json, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, "araclar")
import uret
kasa, cikti, tablo = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
bugun = date.today() if tablo else date(2026, 11, 16)
veri, _ = uret.uret_uyarili(kasa, bugun, Path(tablo) if tablo else None)
cikti.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")
' "$KASA" "$DUZ" "$TABLO"

printf '%s\n' onizleme | node araclar/sifrele.mjs "$DUZ" "$HEDEF/veri.sifreli.json" .yerel/onizleme-salt.txt
echo "Önizleme hazır (deneme parolası: onizleme)."
echo "Sunucu: python3 -m http.server 8001 -d $HEDEF"
