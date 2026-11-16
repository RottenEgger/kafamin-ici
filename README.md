# Kafamın İçi

Kişisel, şifreli bir 3B gökyüzü haritası. Notlardan üretilen veri tarayıcıda
parolayla açılır; parola olmadan sayfada yalnızca bir kilit ekranı görünür.
Bu depodaki veri dosyası (`docs/veri.sifreli.json`) şifrelidir, içeriği okunamaz.

## Yerelde açma

```
cd docs
python3 -m http.server 8000
```

Sonra tarayıcıda `http://localhost:8000` adresini aç.

## Testler

```
python3 -m unittest discover -s testler
node --test testler/*.test.mjs
```

(Node'da `node --test testler/` biçimi çalışmaz; dosya desenini yukarıdaki gibi ver.)

## Parolayı belirleme

Bir kez, kendi Terminal'inde çalıştır:

```
bash araclar/kur_parola.sh
```

Parolayı Terminal sorar ve ekrana yazmaz; macOS Anahtar Zinciri'ne kaydedilir.
Uzun bir parola cümlesi seç ve güvenli bir yere de kaydet. Unutursan veri açılamaz.
Parolada Türkçe harf varsa Anahtar Zinciri onu onaltılık (hex) metin olarak verir; şifreleme betiği bunu otomatik düz parolaya çevirir.

Kaydedilen anahtar tarayıcıda, `rottenegger.github.io` kaynağının (origin) tamamı için saklanır;
yani aynı kaynaktaki başka siteler de bu anahtara erişebilir. Özel bir alan adı (custom domain)
kullanmak bunu ayırır; ileride yapılabilir.

## Yayınlama

```
bash araclar/yayinla.sh
```

Betik sırayla şunları yapar:

1. Kasadan düz veriyi üretir (`.yerel/` içinde, GitHub'a gitmez).
2. Veri bir önceki seferle aynıysa "Değişiklik yok" der ve durur.
3. Değiştiyse parolayı Anahtar Zinciri'nden okuyup veriyi şifreler.
4. Yalnızca şifreli dosyayı kaydeder (commit) ve GitHub'a gönderir.

Not kasasının yolu varsayılan olarak `~/Desktop/İkinci Beyin`'dir;
başka yer için `KASA=/yol bash araclar/yayinla.sh` yaz.

Site GitHub Pages ile `main` dalının `docs` klasöründen yayınlanır.
