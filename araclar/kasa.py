"""Kasa okuyucu: Obsidian kasasını (markdown notları) okuyup düz Python verisine çevirir.

Yalnız standart kütüphane kullanır. Bozuk bir not tüm işi durdurmaz;
atlanır ve `Kasa.uyarilar` listesine yazılır.
"""
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

GIZLI_AD = "Gizli bağlantılar"
SON_GUN = 7  # "son 7 gün": bugün ve önceki 6 gün

LINK = re.compile(r"\[\[([^\]|#]+)")
MADDE = re.compile(r"^\s*- \[([ xX])\]\s*(.*)$")
GUNLUK_AD = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
# Proje kartındaki günlük satırı: "- 2026-11-25: ..." ya da "- 2026-11-25 — ..."
GUNLUK_SATIRI = re.compile(r"^\s*- (\d{4}-\d{2}-\d{2})\s*(?::|—|–|-)\s*(.+)$")
SON_SATIR_SINIRI = 120  # pano satırında gösterilecek en çok karakter


@dataclass
class Alan:
    ad: str
    hassas: bool
    projeler: list[str]


@dataclass
class Not:
    ad: str
    klasor: str  # frontmatter'daki `klasor` (projenin bilgisayardaki klasörü)
    fm: dict
    amac: str
    kaldigim: str
    sonraki: str
    durum: str
    tarih: date | None
    son: tuple[date, str] | None = None  # `## Günlük` bölümündeki en üst satır (tarih, metin)


@dataclass
class Gorev:
    id: str
    metin: str
    bitti: bool
    ilk_tarih: date
    son_tarih: date
    linkler: list[str]


@dataclass
class Kasa:
    alanlar: list[Alan] = field(default_factory=list)
    projeler: list[Not] = field(default_factory=list)
    fikirler: list[Not] = field(default_factory=list)
    kaynaklar: list[Not] = field(default_factory=list)
    dersler: list[str] = field(default_factory=list)
    gorevler: list[Gorev] = field(default_factory=list)
    ilerleyen: set[str] = field(default_factory=set)
    baglantilar: dict[str, set[str]] = field(default_factory=dict)
    uyarilar: list[str] = field(default_factory=list)


def kucuk_harf(metin: str) -> str:
    """Türkçe güvenli küçük harf: İ->i, I->ı önce, sonra lower()."""
    return metin.replace("İ", "i").replace("I", "ı").lower()


def tirnak_at(deger: str) -> str:
    """Değeri saran tek bir eşleşen tırnak çiftini ('..' ya da "..") atar."""
    if len(deger) >= 2 and deger[0] == deger[-1] and deger[0] in "\"'":
        return deger[1:-1].strip()
    return deger


def oku_frontmatter(metin: str) -> tuple[dict[str, str], str]:
    """Baştaki `---` arası `anahtar: değer` satırlarını ve gövdeyi döndürür."""
    satirlar = metin.lstrip("\ufeff").splitlines()
    if not satirlar or satirlar[0].strip() != "---":
        return {}, metin
    for i in range(1, len(satirlar)):
        if satirlar[i].strip() == "---":
            fm = {}
            for satir in satirlar[1:i]:
                if ":" in satir:
                    anahtar, deger = satir.split(":", 1)
                    fm[anahtar.strip()] = tirnak_at(deger.strip())
            return fm, "\n".join(satirlar[i + 1:]) + "\n"
    raise ValueError("frontmatter kapanmıyor")


def kimlik(metin: str) -> str:
    """Yapılacak maddesinin kimliği: sadeleştirilmiş metnin ilk 40 karakteri."""
    s = kucuk_harf(metin)
    for atilacak in ("[[", "]]", "**", "~~"):
        s = s.replace(atilacak, "")
    s = " ".join(s.split())
    return "gorev:" + s[:40]


def temiz_metin(metin: str) -> str:
    """Obsidian işaretlerini atar: [[bağlantı]], **kalın**, ~~üstü çizili~~."""
    metin = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", metin)  # [[Hedef|Görünen]] -> Görünen
    metin = re.sub(r"\[\[([^\]#|]*)#[^\]]*\]\]", r"\1", metin)  # [[Not#Başlık]] -> Not
    for atilacak in ("[[", "]]", "**", "~~"):
        metin = metin.replace(atilacak, "")
    return " ".join(metin.split())


def son_gunluk_satiri(govde: str) -> tuple[date, str] | None:
    """`## Günlük` bölümündeki ilk geçerli tarihli satır: (tarih, sade metin). Yoksa None.

    Kartlarda en yeni satır en üste yazılır; bu yüzden ilk geçerli satır en sonuncudur.
    """
    gunlukte = False
    for satir in govde.splitlines():
        if satir.startswith("#"):
            gunlukte = "günlük" in kucuk_harf(satir)
            continue
        if not gunlukte:
            continue
        m = GUNLUK_SATIRI.match(satir)
        if m and (gun := tarih_cozumle(m.group(1))) is not None:
            return gun, temiz_metin(m.group(2))[:SON_SATIR_SINIRI]
    return None


def linkler(metin: str) -> list[str]:
    return [h.strip() for h in LINK.findall(metin)]


def satir_degeri(govde: str, etiket: str) -> str:
    """`**Etiket:** değer` satırının değerini döndürür (yoksa boş)."""
    m = re.search(r"^\*\*" + re.escape(etiket) + r":\*\*\s*(.*)$", govde, re.M)
    return m.group(1).strip() if m else ""


def tarih_cozumle(deger: str) -> date | None:
    try:
        return date.fromisoformat(deger)
    except ValueError:
        return None


def not_olustur(yol: Path, fm: dict, govde: str) -> Not:
    tarih = tarih_cozumle(fm.get("tarih", "")) or tarih_cozumle(fm.get("dogdugu_tarih", ""))
    if tarih is None:  # frontmatter'da yoksa dosyanın değişme günü
        tarih = datetime.fromtimestamp(yol.stat().st_mtime).date()
    return Not(
        ad=yol.stem,
        klasor=fm.get("klasor", ""),
        fm=fm,
        amac=satir_degeri(govde, "Amaç"),
        kaldigim=satir_degeri(govde, "Kaldığım yer"),
        sonraki=fm.get("sonraki_adim", ""),
        durum=fm.get("durum", ""),
        tarih=tarih,
        son=son_gunluk_satiri(govde),
    )


def alan_projeleri(govde: str) -> list[str]:
    """Başlığında "projeler" geçen bölümdeki `- [[Ad]]` satırları."""
    projeler = []
    icerde = False
    for satir in govde.splitlines():
        if satir.startswith("#"):
            icerde = "projeler" in kucuk_harf(satir)
        elif icerde and satir.lstrip().startswith("- "):
            projeler += linkler(satir)
    return projeler


def dersleri_bul(govde: str) -> list[str]:
    m = re.search(r"^Dersler:\s*(.+)$", govde, re.M)
    if not m:
        return []
    return [d.strip() for d in m.group(1).strip().rstrip(".").split(",") if d.strip()]


def oku_gunluk(govde: str):
    """Günlük notundan (maddeler, yapılanlar) çıkarır.

    maddeler: [(bitti, metin)]; yapilanlar: "Bugün ne yaptım?" ve `[x]` satırları.
    """
    maddeler, yapilanlar = [], []
    bolum = ""
    for satir in govde.splitlines():
        if satir.startswith("#"):
            bolum = kucuk_harf(satir)
            continue
        m = MADDE.match(satir)
        if m:
            bitti = m.group(1) in "xX"
            maddeler.append((bitti, m.group(2).strip()))
            if bitti:
                yapilanlar.append(m.group(2))
        elif "bugün ne yaptım" in bolum and satir.lstrip().startswith("- "):
            yapilanlar.append(satir)
    return maddeler, yapilanlar


def md_dosyalari(klasor: Path) -> list[Path]:
    """Klasördeki (alt klasörler hariç) .md dosyaları, ada göre sıralı."""
    if not klasor.is_dir():
        return []
    return sorted(p for p in klasor.glob("*.md") if p.is_file())


def oku_kasa(kok: Path, bugun: date) -> Kasa:
    kasa = Kasa()

    def oku_notlar(klasor: str):
        """Her dosya için (yol, fm, govde) verir; bozuk dosyayı uyarıyla atlar."""
        for yol in md_dosyalari(kok / klasor):
            try:
                fm, govde = oku_frontmatter(yol.read_text(encoding="utf-8"))
                yield yol, fm, govde
            except Exception as hata:
                kasa.uyarilar.append(f"{yol.stem}: okunamadı ({hata})")

    for yol, fm, govde in oku_notlar("30 Alanlar"):
        kasa.alanlar.append(Alan(yol.stem, fm.get("hassas", "").lower() == "evet", alan_projeleri(govde)))
        kasa.dersler += dersleri_bul(govde)
        kasa.baglantilar[yol.stem] = set(linkler(govde))

    for klasor, liste in (("20 Projeler", kasa.projeler), ("40 Fikirler", kasa.fikirler),
                          ("50 Kaynaklar", kasa.kaynaklar)):
        for yol, fm, govde in oku_notlar(klasor):
            if yol.stem == GIZLI_AD:  # bağlantı notu düğüm değil; gizli.py okur
                continue
            try:
                liste.append(not_olustur(yol, fm, govde))
                kasa.baglantilar[yol.stem] = set(linkler(govde))
            except Exception as hata:
                kasa.uyarilar.append(f"{yol.stem}: okunamadı ({hata})")

    proje_adlari = {p.ad for p in kasa.projeler}
    gorevler: dict[str, Gorev] = {}
    for yol, _fm, govde in oku_notlar("10 Günlük"):  # ada göre sıralı = tarihe göre sıralı
        m = GUNLUK_AD.match(yol.stem)
        if not m:
            continue
        try:
            gun = date(*map(int, m.groups()))
        except ValueError:
            kasa.uyarilar.append(f"{yol.stem}: günlük adı geçerli bir tarih değil")
            continue
        maddeler, yapilanlar = oku_gunluk(govde)
        for bitti, metin in maddeler:
            if not metin:
                continue
            g = gorevler.get(kimlik(metin))
            if g is None:
                g = gorevler[kimlik(metin)] = Gorev(kimlik(metin), metin, bitti, gun, gun, [])
            g.ilk_tarih, g.son_tarih = min(g.ilk_tarih, gun), max(g.son_tarih, gun)
            if gun >= g.son_tarih:  # en son görülen durum geçerli
                g.bitti, g.metin = bitti, metin
            g.linkler += [h for h in linkler(metin) if h not in g.linkler]
        if 0 <= (bugun - gun).days < SON_GUN:
            for satir in yapilanlar:
                kasa.ilerleyen |= {h for h in linkler(satir) if h in proje_adlari}
    kasa.gorevler = list(gorevler.values())
    return kasa
