"""Ana ekran simgesini çizer: koyu gökte altın dört kollu yıldız.

Yalnız standart kütüphane (zlib + struct) kullanır.
Çalıştır: python3 araclar/ikon.py  -> docs/ikon-180.png, docs/ikon-512.png
"""
import math
import struct
import sys
import zlib
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
GOK = (4, 6, 15)          # #04060f
ALTIN = (244, 200, 106)   # #f4c86a
BEYAZ = (255, 244, 214)
# Küçük yıldızlar: (x, y, yarıçap) — boyuttan bağımsız, 0..1 aralığı
KUCUKLER = [(0.18, 0.22, 0.008), (0.82, 0.16, 0.006), (0.74, 0.80, 0.009),
            (0.24, 0.76, 0.006), (0.90, 0.52, 0.005), (0.10, 0.50, 0.005)]


def _karistir(alt, ust, a):
    """ust rengi a (0..1) oranında alt rengin üstüne koyar."""
    a = max(0.0, min(1.0, a))
    return tuple(alt[i] * (1 - a) + ust[i] * a for i in range(3))


def _nokta(x, y):
    """(x, y) 0..1 aralığında; o noktanın rengini (r, g, b) döndürür."""
    renk = GOK
    dx, dy = x - 0.5, y - 0.5
    uzak = math.hypot(dx, dy)
    # yumuşak ışıma
    renk = _karistir(renk, ALTIN, 0.30 * math.exp(-(uzak / 0.16) ** 2))
    # dört kollu yıldız: astroid biçimi |x|^0.5 + |y|^0.5 <= R^0.5
    yaricap = 0.34
    d = (abs(dx) ** 0.5 + abs(dy) ** 0.5) ** 2   # 0 merkezde, kol uçlarında = yaricap
    kenar = yaricap - d
    if kenar > 0:
        renk = _karistir(renk, ALTIN, min(1.0, kenar / 0.012))
        # merkeze doğru beyaza yakın parlak çekirdek
        renk = _karistir(renk, BEYAZ, 0.9 * math.exp(-(uzak / 0.05) ** 2))
    # küçük yıldızlar
    for kx, ky, kr in KUCUKLER:
        m = math.hypot(x - kx, y - ky)
        renk = _karistir(renk, BEYAZ, 0.9 * math.exp(-(m / kr) ** 2))
    return renk


def ciz(boyut):
    """boyut x boyut RGB piksel baytları (2x2 kenar yumuşatma)."""
    satirlar = []
    for j in range(boyut):
        satir = bytearray([0])  # PNG süzgeç baytı: yok
        for i in range(boyut):
            toplam = [0.0, 0.0, 0.0]
            for oy in (0.25, 0.75):
                for ox in (0.25, 0.75):
                    r = _nokta((i + ox) / boyut, (j + oy) / boyut)
                    for k in range(3):
                        toplam[k] += r[k]
            satir.extend(int(round(t / 4)) for t in toplam)
        satirlar.append(bytes(satir))
    return b"".join(satirlar)


def _parca(ad, veri):
    govde = ad + veri
    return struct.pack(">I", len(veri)) + govde + struct.pack(">I", zlib.crc32(govde) & 0xFFFFFFFF)


def png_yaz(yol, boyut):
    ham = ciz(boyut)
    ihdr = struct.pack(">IIBBBBB", boyut, boyut, 8, 2, 0, 0, 0)  # 8 bit, RGB
    icerik = (b"\x89PNG\r\n\x1a\n" + _parca(b"IHDR", ihdr)
              + _parca(b"IDAT", zlib.compress(ham, 9)) + _parca(b"IEND", b""))
    Path(yol).write_bytes(icerik)


def main():
    for boyut in (180, 512):
        yol = KOK / "docs" / f"ikon-{boyut}.png"
        png_yaz(yol, boyut)
        print("yazıldı:", yol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
