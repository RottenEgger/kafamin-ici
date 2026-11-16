"""Sabit yerleşim: her yıldız her gün aynı yerde durur.

Koordinatlar web sayfasındaki 1600x1000 x/y çerçevesindedir; z derinliktir.
Konum, düğüm kimliğinin sha1 özetinden türer (Python'un hash()'i her
çalıştırmada değiştiği için kullanılmaz).
"""
import hashlib
import json
import math
from pathlib import Path

# Tabloda olmayan alanlar sırayla bu yerlere ve renklere oturur.
BOS_YERLER = [(700, 880, 0), (780, 110, -4), (1500, 620, 4), (60, 480, 6)]
BOS_RENKLER = ["#ffd36e", "#ff7ab8", "#9dffea", "#c8a2ff"]

VARSAYILAN_MERKEZ = (800, 500, 0)
EN_AZ_MESAFE = 60
ITME_TURU = 40


def alan_tablosu_oku(yol: Path) -> dict:
    """{"Ad": [x, y, z, "#renk"]} dosyasını okur; yok ya da bozuksa {} döner."""
    try:
        ham = json.loads(Path(yol).read_text(encoding="utf-8"))
        return {ad: (float(v[0]), float(v[1]), float(v[2]), str(v[3])) for ad, v in ham.items()}
    except (OSError, ValueError, TypeError, IndexError, AttributeError):
        return {}


def alan_merkezleri(adlar, tablo=None):
    tablo = tablo or {}
    merkezler = {}
    bos = 0
    for ad in sorted(set(adlar)):
        if ad in tablo:
            merkezler[ad] = tuple(tablo[ad])
        else:
            i = bos % len(BOS_YERLER)
            merkezler[ad] = (*BOS_YERLER[i], BOS_RENKLER[i])
            bos += 1
    return merkezler


def _ozet(kimlik: str) -> int:
    return int(hashlib.sha1(kimlik.encode("utf-8")).hexdigest(), 16)


def _hash_noktasi(kimlik, merkez, alt, ust):
    """Merkez çevresinde, kimlikten türeyen açı ve yarıçapla bir nokta."""
    h = _ozet(kimlik)
    aci = (h % 3600) / 3600 * 2 * math.pi
    yaricap = alt + ((h >> 16) % 1000) / 1000 * (ust - alt)
    return merkez[0] + yaricap * math.cos(aci), merkez[1] + yaricap * math.sin(aci)


def _z(kimlik, taban):
    return taban + ((_ozet(kimlik) >> 32) % 9 - 4)


def _alan_merkezi(dugum, merkezler):
    bulunanlar = [merkezler[a] for a in dugum.get("alanlar", []) if a in merkezler]
    if not bulunanlar:
        return VARSAYILAN_MERKEZ, 1
    n = len(bulunanlar)
    return (sum(m[0] for m in bulunanlar) / n, sum(m[1] for m in bulunanlar) / n,
            sum(m[2] for m in bulunanlar) / n), n


def _it(hareketliler, hepsi):
    """Birbirine 60'tan yakın çiftleri ayırır. Hareketli olmayan düğüm yerinde kalır."""
    for _ in range(ITME_TURU):
        degisti = False
        for a in hepsi:
            for b in hepsi:
                if a["id"] >= b["id"]:
                    continue
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                d = math.hypot(dx, dy)
                if d >= EN_AZ_MESAFE:
                    continue
                if d == 0:  # üst üste: kimlikten türeyen sabit bir yön
                    aci = (_ozet(a["id"] + b["id"]) % 3600) / 3600 * 2 * math.pi
                    dx, dy, d = math.cos(aci), math.sin(aci), 1.0
                acik = (EN_AZ_MESAFE - d) + 0.5
                ux, uy = dx / d, dy / d
                a_gezer = a["id"] in hareketliler
                b_gezer = b["id"] in hareketliler
                if not (a_gezer or b_gezer):
                    continue
                pay_a = 0.5 if (a_gezer and b_gezer) else (1.0 if a_gezer else 0.0)
                a["x"] -= ux * acik * pay_a
                a["y"] -= uy * acik * pay_a
                b["x"] += ux * acik * (1 - pay_a)
                b["y"] += uy * acik * (1 - pay_a)
                degisti = True
        if not degisti:
            break


def yerlestir(dugumler, merkezler):
    """Her düğüme x, y, z yazar. Aynı girdi her zaman aynı konumu verir.

    Düğüm türü: 'uyeler' varsa desen, 'yakin' varsa yapılacak, yoksa proje.
    """
    sirali = sorted(dugumler, key=lambda d: d["id"])
    projeler = [d for d in sirali if not d.get("uyeler") and not d.get("yakin")]
    yapilacaklar = [d for d in sirali if d.get("yakin") and not d.get("uyeler")]
    desenler = [d for d in sirali if d.get("uyeler")]
    kimlikler = {d["id"]: d for d in dugumler}

    for d in projeler:
        merkez, alan_sayisi = _alan_merkezi(d, merkezler)
        alt, ust = (110, 220) if alan_sayisi == 1 else (20, 110)
        d["x"], d["y"] = _hash_noktasi(d["id"], merkez, alt, ust)
        d["z"] = _z(d["id"], merkez[2])
    _it({d["id"] for d in projeler}, projeler)

    for d in yapilacaklar:
        proje = kimlikler.get(d["yakin"])
        if proje is not None and "x" in proje:
            d["x"], d["y"] = _hash_noktasi(d["id"], (proje["x"], proje["y"]), 55, 95)
            d["z"] = _z(d["id"], proje["z"])
        else:  # yakın proje yok: kendi alanında proje gibi durur
            merkez, _ = _alan_merkezi(d, merkezler)
            d["x"], d["y"] = _hash_noktasi(d["id"], merkez, 110, 220)
            d["z"] = _z(d["id"], merkez[2])
    _it({d["id"] for d in yapilacaklar}, projeler + yapilacaklar)

    for d in desenler:
        uyeler = [kimlikler[u] for u in d["uyeler"] if u in kimlikler and "x" in kimlikler[u]]
        if uyeler:
            n = len(uyeler)
            d["x"] = sum(u["x"] for u in uyeler) / n
            d["y"] = sum(u["y"] for u in uyeler) / n
            d["z"] = sum(u["z"] for u in uyeler) / n
        else:
            d["x"], d["y"], d["z"] = VARSAYILAN_MERKEZ
