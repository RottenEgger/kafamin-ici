#!/bin/bash
# Veriyi üretir, şifreler ve GitHub'a gönderir. Veri değişmediyse hiçbir şey yapmaz.
# Test için: PAROLA_KOMUTU parolayı okuyan komutu, GONDER=0 ise "git push"u atlar.
set -euo pipefail
# Zamanlanmış çalışmada PATH dar olabilir (node, python3 Homebrew'da)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")/.."

# Yalnız main dalından yayınlanır (docs/ yalnızca oradan sunulur)
DAL="$(git symbolic-ref --short HEAD 2>/dev/null || true)"
if [ "$DAL" != "main" ]; then
  echo "Hata: yayınlamak için main dalında olmalısın (şu an: ${DAL:-bağımsız HEAD})." >&2
  exit 1
fi

# Yarım kalmış rebase/merge varsa dur (önce elle bitirilmeli)
GITDIR="$(git rev-parse --git-dir)"
if [ -d "$GITDIR/rebase-merge" ] || [ -d "$GITDIR/rebase-apply" ] || [ -f "$GITDIR/MERGE_HEAD" ]; then
  echo "Hata: yarım kalmış bir rebase/merge var; önce elle bitir ya da iptal et (git rebase --abort)." >&2
  exit 1
fi
# Betiğin kendi ürettiği şifreli dosya yarım kalmış olabilir; tek kirli dosya oysa geri al (yeniden üretilir)
SIFRELI="docs/veri.sifreli.json"
KIRLI="$( { git diff --name-only; git diff --cached --name-only; } | sort -u)"
if [ "$KIRLI" = "$SIFRELI" ]; then
  git restore --staged --worktree -- "$SIFRELI"
  echo "Not: önceki çalışmadan yarım kalan $SIFRELI geri alındı."
elif [ -n "$KIRLI" ]; then
  echo "Hata: kayıtlı dosyalarda kaydedilmemiş değişiklik var; önce commit et ya da geri al. Yayın yapılmadı." >&2
  git status --short >&2
  exit 1
fi

KASA="${KASA:-$HOME/Desktop/İkinci Beyin}"
# PAROLA_KOMUTU güvenilir geliştirici kancasıdır (test için); dışarıdan gelen veriyle doldurma.
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
# Parola komut satırına ya da kayda girmez; yalnız boru (stdin) ile gider.
if ! PAROLA="$($PAROLA_KOMUTU 2>/dev/null)" || [ -z "$PAROLA" ]; then
  echo "Hata: parola Anahtar Zinciri'nden okunamadı. Önce bir kez 'bash araclar/kur_parola.sh' çalıştır." >&2
  exit 1
fi
printf '%s\n' "$PAROLA" | node araclar/sifrele.mjs .yerel/veri.json docs/veri.sifreli.json .yerel/salt.txt
unset PAROLA

# 4) Yalnızca şifreli dosya kaydedilir ve gönderilir.
git add docs/veri.sifreli.json
if git diff --cached --quiet -- docs/veri.sifreli.json; then
  # Şifreli dosya zaten kayıtlıyla aynı (şifreleme her seferinde farklı çıktığı
  # için pratikte olmaz); yine de durumu kaydedip çık.
  echo "$YENI" > .yerel/ozet.txt
  echo "Değişiklik yok."
  exit 0
fi
git commit -q -m "Veri güncellendi" -- docs/veri.sifreli.json
if [ "$GONDER" != "0" ]; then
  # Uzaktaki değişiklik varsa üstüne al; olmazsa rebase'i geri al ve dur (git'in hatası görünür kalır)
  if ! git pull --rebase -q origin main; then
    git rebase --abort 2>/dev/null || true
    echo "Hata: GitHub'dan güncel hâl alınamadı: bağlantı sorunu ya da çakışma. Yayın yapılmadı, yerel kayıt duruyor." >&2
    echo "Bu bilgisayardan başka yerde bu depoda değişiklik yapmadıysan: git -C \"$(pwd)\" reset --hard origin/main  ve sonra betiği yeniden çalıştır." >&2
    exit 1
  fi
  git push -q origin main
  echo "$YENI" > .yerel/ozet.txt  # özet yalnızca başarılı gönderimden sonra
  echo "Veri güncellendi ve GitHub'a gönderildi."
else
  echo "$YENI" > .yerel/ozet.txt
  echo "Veri güncellendi (GONDER=0: gönderilmedi)."
fi
