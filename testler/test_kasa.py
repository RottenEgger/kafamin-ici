import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))

import kasa  # noqa: E402

BUGUN = date(2026, 11, 16)
ORNEK = KOK / "testler" / "ornek_kasa"


class KasaTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kasa = kasa.oku_kasa(ORNEK, BUGUN)

    def gorev(self, metin):
        return next(g for g in self.kasa.gorevler if g.id == kasa.kimlik(metin))

    def test_kimlik_turkce_harfler(self):
        self.assertEqual(kasa.kimlik("Dizi İzle"), kasa.kimlik("dizi izle"))
        self.assertEqual(kasa.kimlik("**IŞIK** al"), "gorev:ışık al")

    def test_frontmatter_tirnaklari_atilir(self):
        fm, _ = kasa.oku_frontmatter("---\na: \"evet\"\nb: 'evet'\nc: \"x'\nd: 'iç \"tırnak\"'\n---\n")
        self.assertEqual(fm, {"a": "evet", "b": "evet", "c": "\"x'", "d": "iç \"tırnak\""})

    def test_frontmatter_ve_govde(self):
        fm, govde = kasa.oku_frontmatter("---\ndurum: aktif\nklasor: ~/x\n---\n# Baslik\n")
        self.assertEqual(fm, {"durum": "aktif", "klasor": "~/x"})
        self.assertEqual(govde, "# Baslik\n")

    def test_acik_gorev_tekrar_tek_dugum(self):
        fatura = [g for g in self.kasa.gorevler if g.id == kasa.kimlik("Fatura öde")]
        self.assertEqual(len(fatura), 1)
        self.assertEqual(fatura[0].ilk_tarih, date(2026, 11, 15))
        self.assertEqual(fatura[0].son_tarih, date(2026, 11, 16))
        self.assertFalse(fatura[0].bitti)

    def test_sonra_isaretlenen_bitti(self):
        kitap = self.gorev("Kitabı bitir")
        self.assertIs(kitap.bitti, True)
        self.assertEqual(kitap.ilk_tarih, date(2026, 11, 14))

    def test_eski_acik_maddeler_okunur(self):
        self.assertEqual(self.gorev("Yirmi günlük açık iş").ilk_tarih, date(2026, 10, 27))
        self.assertEqual(self.gorev("Kırk günlük açık iş").ilk_tarih, date(2026, 10, 7))

    def test_gorev_linkleri(self):
        self.assertEqual(self.gorev("Domates fidesi al [[Bahçe]]").linkler, ["Bahçe"])

    def test_proje_alanlari(self):
        alanlar = {a.ad: a for a in self.kasa.alanlar}
        self.assertIn("Kitap Kulübü", alanlar["İş"].projeler)
        self.assertIn("Kitap Kulübü", alanlar["Okul"].projeler)
        self.assertEqual(alanlar["Hayat"].projeler, ["Bahçe"])

    def test_proje_alanlari_dolu(self):
        bahce = next(p for p in self.kasa.projeler if p.ad == "Bahçe")
        self.assertEqual(bahce.durum, "aktif")
        self.assertEqual(bahce.amac, "Balkonda küçük bir bahçe kurmak.")
        self.assertEqual(bahce.kaldigim, "Saksılar alındı, toprak bekliyor.")
        self.assertEqual(bahce.sonraki, "Domates fidelerini dik")
        self.assertEqual(bahce.tarih, date(2026, 11, 16))

    def test_ilerleyen(self):
        self.assertIn("Bahçe", self.kasa.ilerleyen)
        self.assertNotIn("Kitap Kulübü", self.kasa.ilerleyen)

    def test_dersler(self):
        self.assertEqual(self.kasa.dersler, ["Matematik", "Tarih"])

    def test_fikirler(self):
        self.assertEqual([f.ad for f in self.kasa.fikirler], ["Mavi Kapı"])
        self.assertEqual(self.kasa.fikirler[0].durum, "tohum")

    def test_kaynaklar_ve_alt_klasor_haric(self):
        adlar = {k.ad for k in self.kasa.kaynaklar}
        self.assertEqual(adlar, {"Yeni Kaynak", "Eski Kaynak"})
        self.assertNotIn("Akış Notu", adlar)
        yeni = next(k for k in self.kasa.kaynaklar if k.ad == "Yeni Kaynak")
        self.assertEqual(yeni.tarih, date(2026, 11, 15))

    def test_baglantilar(self):
        self.assertEqual(self.kasa.baglantilar["Kitap Kulübü"], {"İş", "Okul", "Mavi Kapı"})

    def test_hassas_alan(self):
        alanlar = {a.ad: a for a in self.kasa.alanlar}
        self.assertIs(alanlar["Para"].hassas, True)
        self.assertIs(alanlar["Hayat"].hassas, False)

    def test_bozuk_not_atlanir(self):
        adlar = [p.ad for p in self.kasa.projeler]
        self.assertNotIn("Bozuk Not", adlar)
        self.assertNotIn("Bozuk Not", self.kasa.baglantilar)
        self.assertTrue(any("Bozuk Not" in u for u in self.kasa.uyarilar))


class TarihYedekTesti(unittest.TestCase):
    def setUp(self):
        self.gecici = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.gecici)
        self.kok = self.gecici / "kasa"
        shutil.copytree(ORNEK, self.kok)

    def test_dogdugu_tarih_yedegi(self):
        (self.kok / "40 Fikirler" / "Mavi Kapı.md").write_text(
            "---\ndurum: tohum\ndogdugu_tarih: 2026-09-05\n---\n# Mavi Kapı\n", encoding="utf-8")
        k = kasa.oku_kasa(self.kok, BUGUN)
        self.assertEqual(k.fikirler[0].tarih, date(2026, 9, 5))

    def test_mtime_yedegi(self):
        yol = self.kok / "40 Fikirler" / "Mavi Kapı.md"
        yol.write_text("---\ndurum: tohum\n---\n# Mavi Kapı\n", encoding="utf-8")
        an = datetime(2026, 8, 3, 12, 0).timestamp()
        os.utime(yol, (an, an))
        k = kasa.oku_kasa(self.kok, BUGUN)
        self.assertEqual(k.fikirler[0].tarih, date(2026, 8, 3))

    def test_gecersiz_gunluk_adi_atlanir(self):
        for ad in ("2026-02-30", "2026-13-01"):
            (self.kok / "10 Günlük" / f"{ad}.md").write_text("- [ ] Hayalet iş\n", encoding="utf-8")
        k = kasa.oku_kasa(self.kok, BUGUN)
        self.assertTrue(any("2026-02-30" in u for u in k.uyarilar))
        self.assertTrue(any("2026-13-01" in u for u in k.uyarilar))
        self.assertNotIn(kasa.kimlik("Hayalet iş"), [g.id for g in k.gorevler])


if __name__ == "__main__":
    unittest.main()


class TestSonGunluk(unittest.TestCase):
    """Proje kartının `## Günlük` bölümündeki en üst tarihli satır."""

    def test_iki_nokta_bicimi(self):
        govde = "# P\n\n## Günlük\n- 2026-11-15: **Kalın** iş [[Bahçe]] yapıldı\n- 2026-11-10: eski\n"
        self.assertEqual(kasa.son_gunluk_satiri(govde), (date(2026, 11, 15), "Kalın iş Bahçe yapıldı"))

    def test_uzun_tire_bicimi(self):
        self.assertEqual(kasa.son_gunluk_satiri("## Günlük\n- 2026-11-14 — tire ile\n"),
                         (date(2026, 11, 14), "tire ile"))

    def test_gunluk_yoksa_none(self):
        self.assertIsNone(kasa.son_gunluk_satiri("# P\n\n**Amaç:** x\n"))

    def test_bozuk_tarih_atlanir_sonraki_alinir(self):
        self.assertEqual(kasa.son_gunluk_satiri("## Günlük\n- 2026-13-40: bozuk\n- 2026-11-01: iyi\n"),
                         (date(2026, 11, 1), "iyi"))

    def test_baska_bolumdeki_tarihli_satir_sayilmaz(self):
        self.assertIsNone(kasa.son_gunluk_satiri("## Notlar\n- 2026-11-15: değil\n"))

    def test_gunluk_bittikten_sonraki_bolum_sayilmaz(self):
        self.assertIsNone(kasa.son_gunluk_satiri("## Günlük\nhenüz yok\n## Notlar\n- 2026-11-15: değil\n"))

    def test_metin_120_karakter(self):
        self.assertEqual(len(kasa.son_gunluk_satiri("## Günlük\n- 2026-11-15: " + "a" * 300 + "\n")[1]), 120)

    def test_not_olusturda_son(self):
        k = kasa.oku_kasa(ORNEK, BUGUN)
        bahce = next(p for p in k.projeler if p.ad == "Bahçe")
        self.assertEqual(bahce.son, (date(2026, 11, 15), "Saksılar alındı"))
        kulup = next(p for p in k.projeler if p.ad == "Kitap Kulübü")
        self.assertIsNone(kulup.son)
