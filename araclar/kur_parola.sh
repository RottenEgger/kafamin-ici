#!/bin/bash
# Yayın parolasını macOS Anahtar Zinciri'ne (Keychain) kaydeder.
# Parolayı Terminal sorar ve ekrana yazmaz. Bunu sen çalıştırırsın.
# Uzun bir parola cümlesi seç ve bir yere (ör. Parolalar uygulaması) kaydet:
# unutursan şifreli veri açılamaz.
set -euo pipefail

security add-generic-password -U -a "$USER" -s kafamin-ici -w
echo "Parola Anahtar Zinciri'ne kaydedildi (kayıt adı: kafamin-ici)."
