import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))

import yerlesim  # noqa: E402

TABLO = {
    "İş": (300, 280, -14, "#ff9f7a"),
    "Okul": (1150, 300, 8, "#5fd4ff"),
}
MERKEZLER = yerlesim.alan_merkezleri(["İş", "Okul"], TABLO)


def proje(i, alanlar=("İş",)):
    return {"id": f"proje-{i}", "alanlar": list(alanlar), "yakin": None}


def uzaklik(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def konumlar(dugumler):
    return {d["id"]: (d["x"], d["y"], d["z"]) for d in dugumler}


class YerlesimTesti(unittest.TestCase):
    def test_ayni_girdi_ayni_cikti(self):
        a = [proje(i) for i in range(12)]
        b = [proje(i) for i in range(12)]
        yerlesim.yerlestir(a, MERKEZLER)
        yerlesim.yerlestir(b, MERKEZLER)
        self.assertEqual(konumlar(a), konumlar(b))

    def test_minimum_mesafe(self):
        d = [proje(i) for i in range(25)] + [proje(100 + i, ("Okul",)) for i in range(10)]
        yerlesim.yerlestir(d, MERKEZLER)
        for i in range(len(d)):
            for j in range(i + 1, len(d)):
                self.assertGreaterEqual(uzaklik(d[i], d[j]), 60, (d[i]["id"], d[j]["id"]))

    def test_yeni_dugum_digerlerini_az_oynatir(self):
        eski = [proje(i) for i in range(15)]
        yerlesim.yerlestir(eski, MERKEZLER)
        once = konumlar(eski)
        yeni = [proje(i) for i in range(15)] + [proje("yeni")]
        yerlesim.yerlestir(yeni, MERKEZLER)
        sonra = konumlar(yeni)
        for id_, (x, y, _z) in once.items():
            self.assertLessEqual(math.hypot(sonra[id_][0] - x, sonra[id_][1] - y), 40, id_)

    def test_iki_alanli_proje_arada(self):
        d = [proje(1, ("İş", "Okul"))]
        yerlesim.yerlestir(d, MERKEZLER)
        ox = (300 + 1150) / 2
        oy = (280 + 300) / 2
        self.assertLess(math.hypot(d[0]["x"] - ox, d[0]["y"] - oy), 150)

    def test_yakin_projeye_yakin(self):
        d = [proje(i) for i in range(8)]
        d.append({"id": "yap-1", "alanlar": ["İş"], "yakin": "proje-3"})
        d.append({"id": "yap-2", "alanlar": ["İş"], "yakin": "proje-3"})
        yerlesim.yerlestir(d, MERKEZLER)
        p = next(x for x in d if x["id"] == "proje-3")
        for y in d[-2:]:
            self.assertLessEqual(uzaklik(y, p), 130)

    def test_bos_alan_merkezi_var(self):
        m = yerlesim.alan_merkezleri(["Sağlık"])
        x, y, z = yerlesim.BOS_YERLER[0]
        self.assertEqual(m["Sağlık"], (x, y, z, "#ffd36e"))

    def test_tablodaki_alan_tablodan_gelir(self):
        m = yerlesim.alan_merkezleri(["Sağlık", "İş"], TABLO)
        self.assertEqual(m["İş"], (300, 280, -14, "#ff9f7a"))
        self.assertEqual(m["Sağlık"][:3], yerlesim.BOS_YERLER[0])

    def test_alan_tablosu_oku(self):
        with tempfile.TemporaryDirectory() as t:
            yol = Path(t) / "alanlar.json"
            yol.write_text(json.dumps({"İş": [300, 280, -14, "#ff9f7a"]}), encoding="utf-8")
            self.assertEqual(yerlesim.alan_tablosu_oku(yol), {"İş": (300, 280, -14, "#ff9f7a")})
            self.assertEqual(yerlesim.alan_tablosu_oku(Path(t) / "yok.json"), {})
            yol.write_text("bozuk{", encoding="utf-8")
            self.assertEqual(yerlesim.alan_tablosu_oku(yol), {})

    def test_bos_yer_baska_alan_cikinca_kaymaz(self):
        tablo = {"Sağlık": (*yerlesim.BOS_YERLER[0], yerlesim.BOS_RENKLER[0])}
        m = yerlesim.alan_merkezleri(["Aile", "Sağlık"], tablo)
        self.assertEqual(m["Sağlık"][:3], yerlesim.BOS_YERLER[0])
        self.assertEqual(m["Aile"], (*yerlesim.BOS_YERLER[1], yerlesim.BOS_RENKLER[1]))

    def test_desen_baska_yildizin_ustune_binmez(self):
        # p02 ile p16'nın orta noktası, uye olmayan p15'e ~1 birim yakın düşer
        def kur():
            d = [{"id": f"p{i:02d}", "alanlar": ["İş"], "yakin": None} for i in range(20)]
            d.append({"id": "desen-1", "alanlar": [], "yakin": None, "uyeler": ["p02", "p16"]})
            return d
        d = kur()
        yerlesim.yerlestir(d, MERKEZLER)
        desen = d[-1]
        for o in d[:-1]:
            self.assertGreaterEqual(uzaklik(desen, o), 60 - 1e-6, o["id"])
        d2 = kur()
        yerlesim.yerlestir(d2, MERKEZLER)
        self.assertEqual(konumlar(d), konumlar(d2))

    def test_desen_uyelerin_ortasinda(self):
        d = [proje(i) for i in range(5)]
        d.append({"id": "desen-1", "alanlar": [], "yakin": None, "uyeler": ["proje-0", "proje-2", "proje-4"]})
        yerlesim.yerlestir(d, MERKEZLER)
        uyeler = [x for x in d if x["id"] in ("proje-0", "proje-2", "proje-4")]
        ox = sum(u["x"] for u in uyeler) / 3
        oy = sum(u["y"] for u in uyeler) / 3
        desen = d[-1]
        self.assertLess(math.hypot(desen["x"] - ox, desen["y"] - oy), 1)


if __name__ == "__main__":
    unittest.main()
