import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))

import gizli  # noqa: E402
from kasa import kimlik  # noqa: E402

ORNEK = KOK / "testler" / "ornek_kasa" / "50 Kaynaklar" / "Gizli bağlantılar.md"


class GizliTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baglar, cls.desenler = gizli.oku_gizli(ORNEK)

    def test_bag_uclari(self):
        b = self.baglar[0]
        self.assertEqual(b.baslik, "Tohum ve bahçe")
        self.assertEqual(b.a, "Bahçe")
        self.assertEqual(b.b, kimlik("Tohum al"))
        self.assertEqual(b.guven, "emin")
        self.assertEqual(b.tarih, date(2026, 11, 16))
        self.assertIn("sulama", b.metin)

    def test_tahmin(self):
        b = self.baglar[1]
        self.assertEqual(b.guven, "tahmin")
        self.assertEqual(b.b, kimlik("Veri Yapıları"))

    def test_yanlis_gizlenir(self):
        self.assertEqual(len(self.baglar), 2)
        self.assertEqual(len(self.desenler), 1)
        self.assertNotIn("Yanlış bulunan", [b.baslik for b in self.baglar])

    def test_guven_yoksa_emin(self):
        with tempfile.TemporaryDirectory() as t:
            y = Path(t) / "g.md"
            y.write_text("## X\n- [[A]] ⟷ Desen: Büyük kararlar\n- bulundu: 2026-11-16\nAçıklama\n",
                         encoding="utf-8")
            baglar, _ = gizli.oku_gizli(y)
        self.assertEqual(baglar[0].guven, "emin")
        self.assertEqual(baglar[0].b, "desen:Büyük kararlar")

    def test_desen_uyeleri(self):
        d = self.desenler[0]
        self.assertEqual(d.baslik, "Büyük kararlar")
        self.assertEqual(d.uyeler, ["Bahçe", kimlik("Tohum al"), "Kitap Kulübü"])
        self.assertEqual(d.tarih, date(2026, 11, 16))
        self.assertIn("aynı kararı", d.metin)

    def test_ilgili_satiri_metne_girmez(self):
        with tempfile.TemporaryDirectory() as t:
            y = Path(t) / "g.md"
            y.write_text("## X\n- [[A]] ⟷ [[B]]\n- bulundu: 2026-11-16\nAçıklama burada.\n\nİlgili: [[Y]]\n",
                         encoding="utf-8")
            baglar, _ = gizli.oku_gizli(y)
        self.assertEqual(baglar[0].metin, "Açıklama burada.")

    def test_bos_dosya(self):
        with tempfile.TemporaryDirectory() as t:
            y = Path(t) / "bos.md"
            y.write_text("", encoding="utf-8")
            self.assertEqual(gizli.oku_gizli(y), ([], []))


if __name__ == "__main__":
    unittest.main()
