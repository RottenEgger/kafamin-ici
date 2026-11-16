import json
import math
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))

import uret  # noqa: E402

ORNEK = KOK / "testler" / "ornek_kasa"
BUGUN = date(2026, 11, 16)

GIZLI_NOT = """---
tur: kaynak
---
# Gizli bağlantılar

## Domates işi
- [[Bahçe]] ⟷ Domates fidesi al [[Bahçe]]
- bulundu: 2026-11-16 · güven: emin
Bahçe için fide almak.

## Biten iş
- [[Bahçe]] ⟷ Kitabı bitir
- bulundu: 2026-11-16
İşaretlenmiş görev; bağ gizlenmeli.

## Ders bağı
- [[Kitap Kulübü]] ⟷ Matematik
- bulundu: 2026-11-16 · güven: tahmin
Düz ders adı ders düğümüne bağlanır.

## Hayalet
- [[Bahçe]] ⟷ [[Olmayan Not]]
- bulundu: 2026-11-16
Ucu olmayan bağ.

## Desen: Tek üyeli
- üyeler: [[Bahçe]] · Olmayan şey
- bulundu: 2026-11-16
Yalnız bir üye çözülür; desen çıkmamalı.
"""


class GeciciKasa(unittest.TestCase):
    """Her test için örnek kasanın geçici bir kopyasını verir."""

    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.addCleanup(self.gecici.cleanup)
        self.kok = Path(self.gecici.name) / "kasa"
        shutil.copytree(ORNEK, self.kok)

    def yaz(self, goreli, icerik):
        yol = self.kok / goreli
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(icerik, encoding="utf-8")

    def dugum(self, veri, id):
        return next(d for d in veri["dugumler"] if d["id"] == id)


class TestSema(GeciciKasa):
    def test_sema(self):
        veri = uret.uret(ORNEK, BUGUN)
        self.assertEqual(set(veri), {"tarih", "alanlar", "dugumler", "acik", "gizli", "buHafta"})
        self.assertEqual(veri["tarih"], "16 Kasım 2026")
        json.dumps(veri, ensure_ascii=False)  # JSON'a çevrilebilmeli
        for a in veri["alanlar"]:
            self.assertEqual(set(a), {"ad", "x", "y", "z", "renk"})
        self.assertEqual({a["ad"] for a in veri["alanlar"]}, {"Hayat", "Okul", "Para", "İş"})
        turler = {d["tur"] for d in veri["dugumler"]}
        self.assertEqual(turler, {"proje", "gorev", "ders", "fikir", "kaynak", "karadelik"})
        kimlikler = [d["id"] for d in veri["dugumler"]]
        self.assertEqual(len(kimlikler), len(set(kimlikler)))
        for d in veri["dugumler"]:
            self.assertTrue({"id", "ad", "tur", "durum", "x", "y", "z", "alan"} <= set(d))
            self.assertIn(d["durum"], {"bitti", "bekliyor", "surekli"})
            self.assertFalse({"alanlar", "yakin", "uyeler"} & set(d))
        self.assertNotIn("Bozuk Not", kimlikler)
        self.assertEqual(self.dugum(veri, "Bahçe")["durum"], "bitti")  # bu hafta ilerledi
        self.assertEqual(self.dugum(veri, "Kitap Kulübü")["durum"], "surekli")
        self.assertEqual(self.dugum(veri, "Mavi Kapı")["durum"], "bekliyor")
        self.assertEqual(self.dugum(veri, "Kitap Kulübü")["alan"], "Okul + İş")
        for g in veri["gizli"]:
            self.assertEqual(set(g), {"a", "b", "baslik", "metin", "guven"})
        for a, b in veri["acik"]:
            self.assertIn(a, kimlikler)
            self.assertIn(b, kimlikler)
        self.assertTrue(set(veri["buHafta"]) <= set(kimlikler))
        self.assertIn("Bahçe", veri["buHafta"])

    def test_deterministik(self):
        self.assertEqual(uret.uret(ORNEK, BUGUN), uret.uret(ORNEK, BUGUN))

    def test_yeni_kaynak_var_eski_yok(self):
        kimlikler = {d["id"] for d in uret.uret(ORNEK, BUGUN)["dugumler"]}
        self.assertIn("Yeni Kaynak", kimlikler)
        self.assertNotIn("Eski Kaynak", kimlikler)

    def test_gizli_notu_kaynak_degil(self):
        veri = uret.uret(ORNEK, BUGUN)
        self.assertFalse([d for d in veri["dugumler"] if "Gizli" in d["id"] or "Gizli" in d["ad"]])


class TestGorevler(GeciciKasa):
    def test_unutulmus_ve_30_gun(self):
        veri = uret.uret(ORNEK, BUGUN)
        yirmi = self.dugum(veri, "gorev:yirmi günlük açık iş")
        self.assertTrue(yirmi["unutulmus"])
        self.assertEqual(yirmi["bekliyorGun"], 20)
        self.assertNotIn("gorev:kırk günlük açık iş", {d["id"] for d in veri["dugumler"]})
        taze = self.dugum(veri, "gorev:fatura öde")
        self.assertNotIn("unutulmus", taze)
        self.assertEqual(taze["bekliyorGun"], 1)

    def test_yapilacagin_alani(self):
        self.yaz("10 Günlük/2026-11-16.md",
                 (self.kok / "10 Günlük/2026-11-16.md").read_text(encoding="utf-8")
                 + "- [ ] Rapor yaz [[İş]]\n- [ ] Eski iş [[Bitmiş Proje]]\n")
        self.yaz("20 Projeler/Bitmiş Proje.md", "---\ndurum: bitti\n---\n# Bitmiş Proje\n")
        veri = uret.uret(self.kok, BUGUN)
        domates = self.dugum(veri, "gorev:domates fidesi al bahçe")
        self.assertEqual(domates["alan"], "Hayat")
        bahce = self.dugum(veri, "Bahçe")
        self.assertLess(math.hypot(domates["x"] - bahce["x"], domates["y"] - bahce["y"]), 130)
        self.assertEqual(self.dugum(veri, "gorev:rapor yaz iş")["alan"], "İş")
        self.assertEqual(self.dugum(veri, "gorev:fatura öde")["alan"], "Hayat")  # bağlantısız
        self.assertEqual(self.dugum(veri, "gorev:eski iş bitmiş proje")["alan"], "Hayat")  # gösterilmeyen proje

    def test_yapilanlar_en_fazla_8(self):
        satirlar = "".join(f"- [x] Bitti {i:02d}\n" for i in range(12))
        self.yaz("10 Günlük/2026-11-16.md", "# 2026-11-16\n" + satirlar)
        veri = uret.uret(self.kok, BUGUN)
        biten = [d for d in veri["dugumler"] if d["tur"] == "gorev" and d["durum"] == "bitti"]
        self.assertEqual(len(biten), 8)

    def test_projeye_bagli_yapilan_dugum_olmaz(self):
        self.yaz("10 Günlük/2026-11-16.md", "# 2026-11-16\n- [x] Saksıları aldım [[Bahçe]]\n")
        veri = uret.uret(self.kok, BUGUN)
        self.assertNotIn("gorev:saksıları aldım bahçe", {d["id"] for d in veri["dugumler"]})
        self.assertEqual(self.dugum(veri, "Bahçe")["durum"], "bitti")


class TestAlanlar(GeciciKasa):
    def test_hassas_alan_metin_yok(self):
        self.yaz("20 Projeler/Bütçe Takibi.md",
                 "---\ndurum: aktif\nsonraki_adim: Tutarları gir\n---\n# Bütçe Takibi\n\n"
                 "**Amaç:** Aylık 5000 lira gelir.\n**Kaldığım yer:** Bakiye 1200.\n")
        self.yaz("30 Alanlar/Para.md",
                 "---\ntur: alan\nhassas: evet\n---\n# Para\n\n## Projeler\n- [[Bütçe Takibi]]\n")
        veri = uret.uret(self.kok, BUGUN)
        butce = self.dugum(veri, "Bütçe Takibi")
        self.assertEqual(butce["alan"], "Para")
        self.assertNotIn("metin", butce)
        self.assertNotIn("sonraki", butce)
        self.assertNotIn("5000", json.dumps(veri, ensure_ascii=False))
        bahce = self.dugum(veri, "Bahçe")
        self.assertIn("metin", bahce)
        self.assertEqual(bahce["sonraki"], "Domates fidelerini dik")

    def test_dersin_alani(self):
        veri = uret.uret(ORNEK, BUGUN)
        for ad in ("Matematik", "Tarih"):
            d = self.dugum(veri, ad)
            self.assertEqual((d["tur"], d["alan"], d["durum"]), ("ders", "Okul", "surekli"))

    def test_yapilacak_proje_gorunmeyen(self):
        self.yaz("20 Projeler/Bahçe.md",
                 "---\ndurum: bırakıldı\n---\n# Bahçe\n\nİlgili: [[Hayat]]\n")
        ids = {d["id"] for d in uret.uret(self.kok, BUGUN)["dugumler"]}
        self.assertNotIn("Bahçe", ids)

    def test_yapisik_alan_tablosu(self):
        tablo = self.kok.parent / "alanlar.json"
        tablo.write_text(json.dumps({"Hayat": [111, 222, 3, "#123456"]}), encoding="utf-8")
        ilk = uret.uret(self.kok, BUGUN, tablo)
        hayat = next(a for a in ilk["alanlar"] if a["ad"] == "Hayat")
        self.assertEqual((hayat["x"], hayat["y"], hayat["z"], hayat["renk"]), (111, 222, 3, "#123456"))
        ham = json.loads(tablo.read_text(encoding="utf-8"))
        self.assertEqual(ham["Hayat"], [111, 222, 3, "#123456"])  # eski satıra dokunulmadı
        self.assertEqual(set(ham), {"Hayat", "Okul", "Para", "İş"})  # yeniler yazıldı
        ikinci = uret.uret(self.kok, BUGUN, tablo)
        self.assertEqual(ilk, ikinci)
        # yeni alan gelince eskiler yerinde kalır, yeni alan yeni boş yere oturur
        self.yaz("30 Alanlar/Sağlık.md", "---\ntur: alan\n---\n# Sağlık\n")
        ucuncu = uret.uret(self.kok, BUGUN, tablo)
        eski = {a["ad"]: (a["x"], a["y"], a["z"], a["renk"]) for a in ilk["alanlar"]}
        yeni = {a["ad"]: (a["x"], a["y"], a["z"], a["renk"]) for a in ucuncu["alanlar"]}
        for ad, deger in eski.items():
            self.assertEqual(yeni[ad], deger)
        self.assertEqual(len({v[:3] for v in yeni.values()}), 5)
        ham = json.loads(tablo.read_text(encoding="utf-8"))
        self.assertIn("Sağlık", ham)

    def test_tablo_yolu_verilmezse_dosya_yazilmaz(self):
        uret.uret(self.kok, BUGUN)
        self.assertFalse((self.kok.parent / "alanlar.json").exists())


class TestBaglar(GeciciKasa):
    def test_bag_ucu_yoksa_dusur(self):
        veri = uret.uret(ORNEK, BUGUN)
        kimlikler = {d["id"] for d in veri["dugumler"]}
        for g in veri["gizli"]:
            self.assertIn(g["a"], kimlikler)
            self.assertIn(g["b"], kimlikler)
        basliklar = {g["baslik"] for g in veri["gizli"]}
        self.assertNotIn("Kitap ve ders", basliklar)  # "Veri Yapıları" düğümü yok
        self.assertNotIn("Yanlış bulunan", basliklar)  # durum: yanlış

    def test_isaretlenen_gorevin_bagi_gizlenir(self):
        self.yaz("50 Kaynaklar/Gizli bağlantılar.md", GIZLI_NOT)
        veri = uret.uret(self.kok, BUGUN)
        basliklar = {g["baslik"] for g in veri["gizli"]}
        self.assertNotIn("Biten iş", basliklar)
        self.assertNotIn("Hayalet", basliklar)
        self.assertIn("Domates işi", basliklar)

    def test_ucu_kimlikle_ve_ders_adiyla_baglanir(self):
        self.yaz("50 Kaynaklar/Gizli bağlantılar.md", GIZLI_NOT)
        veri = uret.uret(self.kok, BUGUN)
        domates = next(g for g in veri["gizli"] if g["baslik"] == "Domates işi")
        self.assertEqual((domates["a"], domates["b"]), ("Bahçe", "gorev:domates fidesi al bahçe"))
        self.assertEqual(domates["guven"], "emin")
        ders = next(g for g in veri["gizli"] if g["baslik"] == "Ders bağı")
        self.assertEqual((ders["a"], ders["b"]), ("Kitap Kulübü", "Matematik"))
        self.assertEqual(ders["guven"], "tahmin")

    def test_desen(self):
        veri = uret.uret(ORNEK, BUGUN)
        desen = self.dugum(veri, "desen:Büyük kararlar")
        self.assertEqual((desen["tur"], desen["durum"], desen["ad"]), ("karadelik", "bekliyor", "Büyük kararlar"))
        kayitlar = [g for g in veri["gizli"] if g["a"] == "desen:Büyük kararlar"]
        self.assertEqual(sorted(g["b"] for g in kayitlar), ["Bahçe", "Kitap Kulübü"])  # "Tohum al" çözülmedi
        self.assertEqual({g["baslik"] for g in kayitlar},
                         {"Kara deliğe çekilen: Bahçe", "Kara deliğe çekilen: Kitap Kulübü"})
        # kara delik üyelerinin ortasında durur
        bahce, kulup = self.dugum(veri, "Bahçe"), self.dugum(veri, "Kitap Kulübü")
        self.assertLess(math.hypot(desen["x"] - (bahce["x"] + kulup["x"]) / 2,
                                   desen["y"] - (bahce["y"] + kulup["y"]) / 2), 80)

    def test_iki_uyesi_cozulmeyen_desen_cikmaz(self):
        self.yaz("50 Kaynaklar/Gizli bağlantılar.md", GIZLI_NOT)
        veri = uret.uret(self.kok, BUGUN)
        self.assertNotIn("desen:Tek üyeli", {d["id"] for d in veri["dugumler"]})

    def test_acik_baglantilar(self):
        veri = uret.uret(ORNEK, BUGUN)
        cift = {tuple(c) for c in veri["acik"]}
        self.assertIn(("Bahçe", "Mavi Kapı"), cift)  # Mavi Kapı -> Bahçe, sıralı çift
        self.assertEqual(len(cift), len(veri["acik"]))  # tekrar yok


class TestSinirlar(GeciciKasa):
    def test_en_fazla_60(self):
        for i in range(80):
            self.yaz(f"50 Kaynaklar/Kaynak {i:02d}.md", f"---\ntarih: 2026-11-{10 + i % 7:02d}\n---\n# Kaynak {i}\n")
        veri = uret.uret(self.kok, BUGUN)
        self.assertLessEqual(len(veri["dugumler"]), 60)
        # kaynaklar önce düşer: yapılan hâlâ duruyor, en yeni kaynaklar kalmış
        self.assertIn("gorev:kitabı bitir", {d["id"] for d in veri["dugumler"]})
        kaynaklar = [d["id"] for d in veri["dugumler"] if d["tur"] == "kaynak"]
        self.assertTrue(kaynaklar)

    def test_yapilanlar_sonra_duser(self):
        for i in range(51):
            self.yaz(f"40 Fikirler/Fikir {i:02d}.md", f"---\ndurum: tohum\n---\n# Fikir {i}\n")
        veri = uret.uret(self.kok, BUGUN)
        self.assertLessEqual(len(veri["dugumler"]), 60)
        turler = [(d["tur"], d["durum"]) for d in veri["dugumler"]]
        self.assertNotIn("kaynak", [t for t, _ in turler])
        self.assertNotIn(("gorev", "bitti"), turler)
        self.assertEqual(sum(1 for t, _ in turler if t == "fikir"), 52)  # fikirler düşmez

    def test_dusen_dugumun_baglari_da_gider(self):
        for i in range(80):
            self.yaz(f"50 Kaynaklar/Kaynak {i:02d}.md",
                     f"---\ntarih: 2026-11-16\n---\n# Kaynak {i}\n\nİlgili: [[Bahçe]]\n")
        veri = uret.uret(self.kok, BUGUN)
        kimlikler = {d["id"] for d in veri["dugumler"]}
        for a, b in veri["acik"]:
            self.assertTrue(a in kimlikler and b in kimlikler)


class TestHassasSizinti(GeciciKasa):
    def hassas_kur(self):
        self.yaz("20 Projeler/Bütçe Takibi.md",
                 "---\ndurum: aktif\n---\n# Bütçe Takibi\n\n**Amaç:** x\n")
        self.yaz("30 Alanlar/Para.md",
                 "---\ntur: alan\nhassas: evet\n---\n# Para\n\n## Projeler\n- [[Bütçe Takibi]]\n")

    def test_hassas_uclu_bag_ve_desen_metni_gitmez(self):
        self.hassas_kur()
        self.yaz("50 Kaynaklar/Gizli bağlantılar.md",
                 "# Gizli bağlantılar\n\n## Para bağı\n- [[Bütçe Takibi]] ⟷ [[Bahçe]]\n"
                 "- bulundu: 2026-11-16\nGIZLIBAGMETNI bakiye\n\n"
                 "## Desen: Para deseni\n- üyeler: [[Bütçe Takibi]] · [[Bahçe]]\n"
                 "- bulundu: 2026-11-16\nGIZLIDESENMETNI bakiye\n\n"
                 "## Normal bağ\n- [[Bahçe]] ⟷ [[Kitap Kulübü]]\n- bulundu: 2026-11-16\nACIKMETIN\n")
        veri = uret.uret(self.kok, BUGUN)
        ham = json.dumps(veri, ensure_ascii=False)
        self.assertNotIn("GIZLIBAGMETNI", ham)
        self.assertNotIn("GIZLIDESENMETNI", ham)
        self.assertIn("ACIKMETIN", ham)  # hassas olmayan bağ etkilenmez
        self.assertTrue([g for g in veri["gizli"] if g["baslik"] == "Para bağı"])  # bağ yine var

    def test_hassas_alandaki_yapilacak_adi_var_metni_yok(self):
        self.hassas_kur()
        self.yaz("10 Günlük/2026-11-16.md", "# 2026-11-16\n- [ ] Vergiyi öde [[Bütçe Takibi]]\n")
        g = self.dugum(uret.uret(self.kok, BUGUN), "gorev:vergiyi öde bütçe takibi")
        self.assertEqual(g["ad"], "Vergiyi öde Bütçe Takibi")
        self.assertNotIn("metin", g)
        self.assertNotIn("sonraki", g)


class TestUstSinir(GeciciKasa):
    def test_fazla_fikir_en_yeniler_kalir(self):
        for i in range(70):
            self.yaz(f"40 Fikirler/Fikir {i:02d}.md",
                     f"---\ndurum: tohum\ntarih: 2026-10-{1 + i // 3:02d}\n---\n# Fikir {i:02d}\n")
        veri, uyarilar = uret.uret_uyarili(self.kok, BUGUN)
        self.assertLessEqual(len(veri["dugumler"]), 60)
        fikirler = {d["id"] for d in veri["dugumler"] if d["tur"] == "fikir"}
        self.assertIn("Fikir 69", fikirler)
        self.assertNotIn("Fikir 00", fikirler)
        self.assertTrue(any("sınırı için çıkarıldı" in u for u in uyarilar))

    def test_unutulmus_yapilacak_fikirden_sonra_duser(self):
        gunluk = "# 2026-10-27\n" + "".join(f"- [ ] Eski iş {i:02d}\n" for i in range(70))
        self.yaz("10 Günlük/2026-10-27.md", gunluk)
        veri = uret.uret(self.kok, BUGUN)
        self.assertLessEqual(len(veri["dugumler"]), 60)
        self.assertNotIn("Mavi Kapı", {d["id"] for d in veri["dugumler"]})  # fikir önce düştü
        taze = {d["id"] for d in veri["dugumler"] if d["tur"] == "gorev"}
        self.assertIn("gorev:fatura öde", taze)  # taze yapılacak düşmez

    def test_65_proje_hepsi_kalir_ve_uyari(self):
        sil = ["20 Projeler/Bahçe.md", "20 Projeler/Kitap Kulübü.md"]
        for g in sil:
            (self.kok / g).unlink()
        for i in range(65):
            self.yaz(f"20 Projeler/Proje {i:02d}.md", f"---\ndurum: aktif\n---\n# Proje {i:02d}\n")
        veri, uyarilar = uret.uret_uyarili(self.kok, BUGUN)
        projeler = [d for d in veri["dugumler"] if d["tur"] == "proje"]
        self.assertEqual(len(projeler), 65)
        self.assertTrue(any("sınırı aşıldı" in u for u in uyarilar))


class TestBozuk(GeciciKasa):
    def test_bos_ve_bozuk_kasa(self):
        bos = Path(self.gecici.name) / "bos"
        bos.mkdir()
        veri, uyarilar = uret.uret_uyarili(bos, BUGUN)
        self.assertEqual(veri["tarih"], "16 Kasım 2026")
        for anahtar in ("alanlar", "dugumler", "acik", "gizli", "buHafta"):
            self.assertEqual(veri[anahtar], [])
        self.assertEqual(uyarilar, [])
        # kasa klasörü hiç yoksa da çökmez
        veri, _ = uret.uret_uyarili(Path(self.gecici.name) / "yok", BUGUN)
        self.assertEqual(veri["dugumler"], [])
        # bozuk not: uyarı var, harita yine çıkar
        veri, uyarilar = uret.uret_uyarili(ORNEK, BUGUN)
        self.assertTrue(any("Bozuk Not" in u for u in uyarilar))
        self.assertTrue(veri["dugumler"])

    def test_bozuk_gizli_not_cokertmez(self):
        (self.kok / "50 Kaynaklar" / "Gizli bağlantılar.md").write_bytes(b"\xff\xfe bozuk")
        veri, uyarilar = uret.uret_uyarili(self.kok, BUGUN)
        self.assertTrue(veri["dugumler"])
        self.assertTrue(any("Gizli" in u for u in uyarilar))

    def test_atlanan_gizli_bag_uyarida(self):
        _, uyarilar = uret.uret_uyarili(ORNEK, BUGUN)
        self.assertTrue(any("Kitap ve ders" in u for u in uyarilar))


if __name__ == "__main__":
    unittest.main()
