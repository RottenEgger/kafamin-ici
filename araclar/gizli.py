"""Gizli bağlantılar notunu okur: `50 Kaynaklar/Gizli bağlantılar.md`.

Her `## Başlık` bölümü bir bağ ya da (başlık `Desen: ` ile başlıyorsa) bir desendir.
Yalnız standart kütüphane kullanır.
"""
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kasa import kimlik  # noqa: E402

AYIRAC = "⟷"
DESEN_ONEK = "Desen:"
LINK = re.compile(r"^\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]$")
TARIH = re.compile(r"bulundu:\s*(\d{4})-(\d{2})-(\d{2})")
GUVEN = re.compile(r"güven:\s*(\w+)")


@dataclass
class Bag:
    baslik: str
    a: str
    b: str
    metin: str
    guven: str  # "emin" | "tahmin"
    tarih: date | None


@dataclass
class Desen:
    baslik: str
    uyeler: list[str]
    metin: str
    tarih: date | None


def uc_coz(uc: str) -> str:
    """`[[X]]` -> "X"; `Desen: X` -> "desen:X"; düz metin -> kimlik(metin)."""
    uc = uc.strip()
    m = LINK.match(uc)
    if m:
        return m.group(1).strip()
    if uc.startswith(DESEN_ONEK):
        return "desen:" + uc[len(DESEN_ONEK):].strip()
    return kimlik(uc)


def _bolumler(metin: str):
    """(başlık, satırlar) çiftleri; frontmatter ve ilk başlıktan önceki kısım atlanır."""
    satirlar = metin.splitlines()
    if satirlar and satirlar[0].strip() == "---":
        for i in range(1, len(satirlar)):
            if satirlar[i].strip() == "---":
                satirlar = satirlar[i + 1:]
                break
    sonuc, baslik, govde = [], None, []
    for s in satirlar:
        if s.startswith("## "):
            if baslik is not None:
                sonuc.append((baslik, govde))
            baslik, govde = s[3:].strip(), []
        elif baslik is not None:
            govde.append(s)
    if baslik is not None:
        sonuc.append((baslik, govde))
    return sonuc


def _tarih(satir: str) -> date | None:
    m = TARIH.search(satir)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def oku_gizli(yol: Path) -> tuple[list[Bag], list[Desen]]:
    baglar: list[Bag] = []
    desenler: list[Desen] = []
    yol = Path(yol)
    if not yol.exists():
        return baglar, desenler
    for baslik, govde in _bolumler(yol.read_text(encoding="utf-8")):
        madde = [s[2:].strip() for s in govde if s.startswith("- ")]
        # "İlgili: [[X]]" alt satırı not bilgisidir, açıklamaya girmez
        aciklama = " ".join(s.strip() for s in govde
                            if s.strip() and not s.startswith("- ") and not s.strip().startswith("İlgili:"))
        if any(re.match(r"durum:\s*yanlış", m) for m in madde):
            continue
        tarih, guven = None, "emin"
        for m in madde:
            tarih = tarih or _tarih(m)
            g = GUVEN.search(m)
            if g:
                guven = g.group(1)
        if baslik.startswith(DESEN_ONEK):
            uyeler: list[str] = []
            for m in madde:
                if m.startswith("üyeler:"):
                    uyeler = [uc_coz(u) for u in m[len("üyeler:"):].split("·") if u.strip()]
            desenler.append(Desen(baslik[len(DESEN_ONEK):].strip(), uyeler, aciklama, tarih))
            continue
        for m in madde:
            if AYIRAC in m:
                sol, sag = m.split(AYIRAC, 1)
                baglar.append(Bag(baslik, uc_coz(sol), uc_coz(sag), aciklama, guven, tarih))
                break
    return baglar, desenler
