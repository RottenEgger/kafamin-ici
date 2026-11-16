"""Üretici: kasa + gizli bağlantılar + yerleşim -> haritanın çizdiği tek JSON.

Kullanım: python3 -I araclar/uret.py <kasa> <cikti.json> [--bugun YYYY-AA-GG]
Yalnız standart kütüphane kullanır. Bozuk not ya da bağ haritayı durdurmaz;
uyarı listesine yazılır.
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gizli import oku_gizli  # noqa: E402
from kasa import (  # noqa: E402
    GIZLI_AD, SON_GUN, dersleri_bul, kimlik, kucuk_harf, md_dosyalari, oku_frontmatter, oku_kasa,
)
from yerlesim import alan_merkezleri, alan_tablosu_oku, yerlestir  # noqa: E402

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
EN_FAZLA_DUGUM = 60
EN_FAZLA_YAPILAN = 8  # bağlantısız yapılanlar (küçük yıldız) en çok 8
UNUTULMUS_GUN = 14  # bundan eski açık iş "unutulmuş olabilir"
GOSTERME_GUN = 30  # bundan eski açık iş hiç gösterilmez
GORULMEYEN_PROJE = ("bitti", "bırakıldı")
GORULMEYEN_FIKIR = ("projeye döndü", "vazgeçildi")
VARSAYILAN_ALAN = "Hayat"
GIZLI_YOL = ("50 Kaynaklar", GIZLI_AD + ".md")


def tarih_yazisi(gun: date) -> str:
    return f"{gun.day} {AYLAR[gun.month - 1]} {gun.year}"


def son_hafta_mi(gun, bugun: date) -> bool:
    """kasa.py'deki "son 7 gün" kuralının aynısı."""
    return gun is not None and 0 <= (bugun - gun).days < SON_GUN


def temiz_metin(metin: str) -> str:
    for atilacak in ("[[", "]]", "**", "~~"):
        metin = metin.replace(atilacak, "")
    return " ".join(metin.split())


def kisalt(metin: str, sinir: int = 48) -> str:
    return metin if len(metin) <= sinir else metin[:sinir - 1].rstrip() + "…"


def ders_alanlari(kok: Path) -> dict[str, str]:
    """Her dersin hangi alan notunda yazdığı.

    kasa.py yalnız ders adlarını tutuyor, alanını tutmuyor; bu yüzden
    "Dersler:" satırı olan alan notlarını burada bir kez daha okuruz.
    """
    sonuc: dict[str, str] = {}
    for yol in md_dosyalari(kok / "30 Alanlar"):
        try:
            _fm, govde = oku_frontmatter(yol.read_text(encoding="utf-8"))
        except Exception:
            continue  # kasa.py bu notu zaten uyarıya yazdı
        for ders in dersleri_bul(govde):
            sonuc.setdefault(ders, yol.stem)
    return sonuc


def alan_tablosunu_yaz(yol: Path, merkezler: dict, tablo: dict, uyarilar: list[str]) -> None:
    """Yeni atanan alanları tablo dosyasına ekler; eski satırlara dokunmaz."""
    yeniler = {ad: m for ad, m in merkezler.items() if ad not in tablo}
    if not yeniler:
        return
    ham: dict = {}
    if yol.exists():
        try:
            ham = json.loads(yol.read_text(encoding="utf-8"))
            if not isinstance(ham, dict):
                raise ValueError("sözlük değil")
        except (OSError, ValueError) as hata:
            uyarilar.append(f"{yol.name}: okunamadı, üzerine yazılmadı ({hata})")
            return
    for ad, m in yeniler.items():
        ham.setdefault(ad, list(m))
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(ham, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def uret_uyarili(kok: Path, bugun: date, tablo_yolu: Path | None = None) -> tuple[dict, list[str]]:
    """Haritanın JSON verisini ve uyarı listesini döndürür."""
    kok = Path(kok)
    kasa = oku_kasa(kok, bugun)
    uyarilar = list(kasa.uyarilar)

    alan_adlari = [a.ad for a in kasa.alanlar]
    hassas = {a.ad for a in kasa.alanlar if a.hassas}
    yedek = [VARSAYILAN_ALAN] if VARSAYILAN_ALAN in alan_adlari else alan_adlari[:1]

    gorunen_projeler = [p for p in kasa.projeler if kucuk_harf(p.durum) not in GORULMEYEN_PROJE]
    proje_alani: dict[str, list[str]] = {}
    for p in gorunen_projeler:
        listeden = [a.ad for a in kasa.alanlar if p.ad in a.projeler]
        notta = [h for h in sorted(kasa.baglantilar.get(p.ad, ())) if h in alan_adlari]
        proje_alani[p.ad] = listeden or notta or list(yedek)

    def baglantidan_alan(adlar) -> list[str]:
        """Bir notun bağlantılarından alanı bulur: önce alan, sonra proje, yoksa yedek."""
        adlar = sorted(adlar)
        alanlar = [h for h in adlar if h in alan_adlari]
        for h in adlar:
            alanlar += [a for a in proje_alani.get(h, []) if a not in alanlar]
        return alanlar or list(yedek)

    dugumler: list[dict] = []
    kullanilan: set[str] = set()

    def ekle(dugum: dict) -> bool:
        if dugum["id"] in kullanilan:
            uyarilar.append(f"{dugum['id']}: aynı kimlikli ikinci düğüm atlandı")
            return False
        kullanilan.add(dugum["id"])
        dugumler.append(dugum)
        return True

    # Projeler
    for p in gorunen_projeler:
        metin = p.amac or ""
        if p.kaldigim:
            metin = (metin + " Kaldığım yer: " + p.kaldigim).strip()
        ekle({"id": p.ad, "ad": p.ad, "tur": "proje",
              "durum": "bitti" if p.ad in kasa.ilerleyen else "surekli",
              "alanlar": proje_alani[p.ad], "metin": metin, "sonraki": p.sonraki})

    # Dersler
    ders_yeri = ders_alanlari(kok)
    for ders in kasa.dersler:
        alan = ders_yeri.get(ders)
        ekle({"id": ders, "ad": ders, "tur": "ders", "durum": "surekli",
              "alanlar": [alan] if alan else list(yedek), "metin": "", "sonraki": ""})

    # Fikirler
    fikir_tarihi: dict[str, date] = {}
    for f in kasa.fikirler:
        if kucuk_harf(f.durum) in GORULMEYEN_FIKIR:
            continue
        fikir_tarihi[f.ad] = f.tarih or date.min  # tarihsiz fikir en eski sayılır
        ekle({"id": f.ad, "ad": f.ad, "tur": "fikir", "durum": "bekliyor",
              "alanlar": baglantidan_alan(kasa.baglantilar.get(f.ad, ())),
              "metin": f.amac or f.kaldigim, "sonraki": f.sonraki})

    # Kaynaklar: yalnız son 7 günde eklenenler
    kaynaklar = [k for k in kasa.kaynaklar if son_hafta_mi(k.tarih, bugun)]
    kaynak_tarihi: dict[str, date] = {}
    for k in kaynaklar:
        if ekle({"id": k.ad, "ad": k.ad, "tur": "kaynak", "durum": "surekli",
                 "alanlar": baglantidan_alan(kasa.baglantilar.get(k.ad, ())),
                 "metin": k.amac or k.kaldigim, "sonraki": ""}):
            kaynak_tarihi[k.ad] = k.tarih

    # Yapılacaklar ve (bağlantısız) yapılanlar
    proje_adlari = {p.ad for p in gorunen_projeler}
    yapilan_tarihi: dict[str, date] = {}
    unutulmus_tarihi: dict[str, date] = {}
    yapilanlar = []
    for g in kasa.gorevler:
        yakin = next((h for h in g.linkler if h in proje_adlari), None)
        if g.bitti:
            if yakin is None and son_hafta_mi(g.son_tarih, bugun):  # projeye bağlı olan projeyi parlatır
                yapilanlar.append(g)
            continue
        bekleyen = (bugun - g.ilk_tarih).days
        if bekleyen > GOSTERME_GUN:
            continue
        if yakin is not None:
            alanlar = proje_alani[yakin]
        else:
            alanlar = [h for h in g.linkler if h in alan_adlari][:1] or list(yedek)
        dugum = {"id": g.id, "ad": kisalt(temiz_metin(g.metin)), "tur": "gorev", "durum": "bekliyor",
                 "alanlar": alanlar, "yakin": yakin, "metin": temiz_metin(g.metin), "sonraki": "",
                 "bekliyorGun": bekleyen}
        if bekleyen > UNUTULMUS_GUN:
            dugum["unutulmus"] = True
            unutulmus_tarihi[g.id] = g.ilk_tarih
        ekle(dugum)
    yapilanlar.sort(key=lambda g: (g.son_tarih, g.id), reverse=True)
    for g in yapilanlar[:EN_FAZLA_YAPILAN]:
        if ekle({"id": g.id, "ad": kisalt(temiz_metin(g.metin)), "tur": "gorev", "durum": "bitti",
                 "alanlar": [h for h in g.linkler if h in alan_adlari][:1] or list(yedek), "yakin": None,
                 "metin": temiz_metin(g.metin), "sonraki": ""}):
            yapilan_tarihi[g.id] = g.son_tarih

    # Gizli bağlantılar ve desenler
    try:
        baglar, desenler = oku_gizli(kok.joinpath(*GIZLI_YOL))
    except Exception as hata:
        baglar, desenler = [], []
        uyarilar.append(f"{GIZLI_AD}: okunamadı ({hata})")
    biten_gorevler = {g.id for g in kasa.gorevler if g.bitti}

    # Düşürme sırası: önce eski kaynaklar, sonra eski yapılanlar, sonra eski fikirler,
    # en son unutulmuş yapılacaklar. Proje, ders, kara delik ve taze yapılacak hiç düşmez.
    def eskiden_yeniye(tarihler: dict) -> list[str]:
        return [k for k, _ in sorted(tarihler.items(), key=lambda t: (t[1], t[0]))]

    dusurulecek = (eskiden_yeniye(kaynak_tarihi) + eskiden_yeniye(yapilan_tarihi)
                   + eskiden_yeniye(fikir_tarihi) + eskiden_yeniye(unutulmus_tarihi))

    def uc_coz(uc: str, kimlikler: set[str]) -> str | None:
        """Ucu bir düğüm kimliğine çevirir; çözülemezse None."""
        if uc in kimlikler:
            return uc
        if uc.startswith("gorev:"):  # düz metin: bir notun ya da dersin adı olabilir
            for d in dugumler:
                if d["tur"] in ("ders", "proje", "fikir", "kaynak") and d["id"] in kimlikler \
                        and kimlik(d["ad"]) == uc:
                    return d["id"]
        return None

    def desenleri_coz(kimlikler: set[str]) -> list[tuple]:
        sonuc = []
        for d in desenler:
            uyeler = []
            for u in d.uyeler:
                c = uc_coz(u, kimlikler)
                if c is not None and c not in uyeler:
                    uyeler.append(c)
            if len(uyeler) >= 2:
                sonuc.append((d, uyeler))
        return sonuc

    dusen = 0
    while True:
        kimlikler = {d["id"] for d in dugumler}
        cozulen_desenler = desenleri_coz(kimlikler)
        if len(dugumler) + len(cozulen_desenler) <= EN_FAZLA_DUGUM or not dusurulecek:
            break
        atilan = dusurulecek.pop(0)
        dugumler[:] = [d for d in dugumler if d["id"] != atilan]
        dusen += 1
    if dusen:
        uyarilar.append(f"{dusen} düğüm {EN_FAZLA_DUGUM} sınırı için çıkarıldı (eski kaynak/yapılan/fikir/unutulmuş)")
    fazla = len(dugumler) + len(cozulen_desenler) - EN_FAZLA_DUGUM
    if fazla > 0:
        uyarilar.append(f"{fazla} düğüm: {EN_FAZLA_DUGUM} sınırı aşıldı, düşürülecek başka düğüm yok")
    cozulen_idler = {d["id"] for d in dugumler}

    # Kara delikler
    kimlik_ad = {d["id"]: d["ad"] for d in dugumler}
    hassas_idler = {d["id"] for d in dugumler if set(d["alanlar"]) & hassas}
    gizli_kayitlari = []
    desen_dugumleri = []
    for d, uyeler in cozulen_desenler:
        desen_id = "desen:" + d.baslik
        if desen_id in cozulen_idler:
            uyarilar.append(f"{desen_id}: aynı kimlikli ikinci düğüm atlandı")
            continue
        for u in d.uyeler:
            if uc_coz(u, cozulen_idler) is None:
                uyarilar.append(f"desen üyesi atlandı ({d.baslik}): uç bulunamadı: {u}")
        desen_hassas = any(u in hassas_idler for u in uyeler)
        if desen_hassas:
            hassas_idler.add(desen_id)
        desen_dugumleri.append({"id": desen_id, "ad": d.baslik, "tur": "karadelik", "durum": "bekliyor",
                                "alanlar": [], "uyeler": uyeler, "metin": d.metin, "sonraki": ""})
        for u in uyeler:
            gizli_kayitlari.append({"a": desen_id, "b": u, "baslik": "Kara deliğe çekilen: " + kimlik_ad[u],
                                    "metin": "" if desen_hassas else d.metin, "guven": "emin"})
    cozulenler = [c[0] for c in cozulen_desenler]
    for d in desenler:
        if not any(d is c for c in cozulenler):
            uyarilar.append(f"desen atlandı ({d.baslik}): en az 2 üye çözülmeli")
    dugumler += desen_dugumleri
    cozulen_idler |= {d["id"] for d in desen_dugumleri}

    # Gizli bağlar (uçları desen de olabilir)

    for b in baglar:
        if b.a in biten_gorevler or b.b in biten_gorevler:
            continue  # işaretlenen görevin bağı sessizce gizlenir
        a, c = uc_coz(b.a, cozulen_idler), uc_coz(b.b, cozulen_idler)
        if a is None or c is None:
            yok = b.a if a is None else b.b
            uyarilar.append(f"gizli bağ atlandı ({b.baslik}): uç bulunamadı: {yok}")
            continue
        if a == c:
            continue
        gizli_metin = "" if {a, c} & hassas_idler else b.metin  # hassas uçlu bağın açıklaması gitmez
        gizli_kayitlari.append({"a": a, "b": c, "baslik": b.baslik, "metin": gizli_metin, "guven": b.guven})

    # Alan merkezleri ve yerleşim
    tablo = alan_tablosu_oku(tablo_yolu) if tablo_yolu else {}
    merkezler = alan_merkezleri(alan_adlari, tablo)
    if tablo_yolu:
        alan_tablosunu_yaz(Path(tablo_yolu), merkezler, tablo, uyarilar)
    yerlestir(dugumler, merkezler)

    # Çıktı düğümleri
    cikti = []
    for d in dugumler:
        o = {"id": d["id"], "ad": d["ad"], "tur": d["tur"], "durum": d["durum"],
             "x": round(float(d["x"]), 1), "y": round(float(d["y"]), 1), "z": round(float(d["z"]), 1),
             "alan": "Desen" if d["tur"] == "karadelik" else " + ".join(d["alanlar"][:2])}
        if d["id"] not in hassas_idler:  # para/sağlık gibi alanlarda yalnız adlar gider
            o["metin"] = d["metin"]
            if d["sonraki"]:
                o["sonraki"] = d["sonraki"]
        for anahtar in ("bekliyorGun", "unutulmus"):
            if anahtar in d:
                o[anahtar] = d[anahtar]
        cikti.append(o)

    # Açık bağlantılar: notlardaki [[bağlantılar]] (iki ucu da düğüm olanlar)
    kimlikler = {d["id"] for d in dugumler}
    cift: set[tuple[str, str]] = set()
    for kaynak, hedefler in kasa.baglantilar.items():
        if kaynak in kimlikler:
            cift |= {tuple(sorted((kaynak, h))) for h in hedefler if h in kimlikler and h != kaynak}
    for g in kasa.gorevler:
        if g.id in kimlikler:
            cift |= {tuple(sorted((g.id, h))) for h in g.linkler if h in kimlikler and h != g.id}

    bu_hafta = [d["id"] for d in cikti
                if (d["tur"] == "proje" and d["durum"] == "bitti") or d["tur"] == "gorev"]

    veri = {
        "tarih": tarih_yazisi(bugun),
        "alanlar": [{"ad": ad, "x": float(m[0]), "y": float(m[1]), "z": float(m[2]), "renk": m[3]}
                    for ad, m in sorted(merkezler.items())],
        "dugumler": cikti,
        "acik": [list(c) for c in sorted(cift)],
        "gizli": gizli_kayitlari,
        "buHafta": bu_hafta,
    }
    return veri, uyarilar


def uret(kok: Path, bugun: date, tablo_yolu: Path | None = None) -> dict:
    return uret_uyarili(kok, bugun, tablo_yolu)[0]


def main(argumanlar: list[str]) -> int:
    bugun = date.today()
    yollar = []
    i = 0
    while i < len(argumanlar):
        if argumanlar[i] == "--bugun" and i + 1 < len(argumanlar):
            bugun = date.fromisoformat(argumanlar[i + 1])
            i += 2
        else:
            yollar.append(argumanlar[i])
            i += 1
    if len(yollar) != 2:
        print("Kullanım: python3 -I araclar/uret.py <kasa> <cikti.json> [--bugun YYYY-AA-GG]", file=sys.stderr)
        return 2
    kok, cikti = Path(yollar[0]).expanduser(), Path(yollar[1])
    if not kok.is_dir():
        print(f"Hata: kasa klasörü bulunamadı: {kok}", file=sys.stderr)
        return 1
    tablo_yolu = Path(__file__).resolve().parent.parent / ".yerel" / "alanlar.json"
    veri, uyarilar = uret_uyarili(kok, bugun, tablo_yolu)
    # Ne alan ne proje notu okunduysa kasa yanlış yerdedir; boş harita yayınlanmasın
    if not veri["alanlar"] and not any(d["tur"] == "proje" for d in veri["dugumler"]):
        print(f"Hata: {kok} içinde alan ya da proje notu bulunamadı; kasa yolu yanlış olabilir. "
              "Çıktı yazılmadı.", file=sys.stderr)
        return 1
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for u in uyarilar:
        print("uyarı:", u, file=sys.stderr)
    turler: dict[str, int] = {}
    for d in veri["dugumler"]:
        turler[d["tur"]] = turler.get(d["tur"], 0) + 1
    ozet = ", ".join(f"{t}: {n}" for t, n in sorted(turler.items()))
    print(f"{len(veri['dugumler'])} düğüm ({ozet}); {len(veri['alanlar'])} alan; "
          f"{len(veri['acik'])} açık, {len(veri['gizli'])} gizli bağlantı; {len(uyarilar)} uyarı")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
