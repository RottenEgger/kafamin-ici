import struct
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))

import ikon  # noqa: E402


class IkonTesti(unittest.TestCase):
    def test_png_imzasi_ve_boyut(self):
        with tempfile.TemporaryDirectory() as t:
            for boyut in (180, 512):
                yol = Path(t) / f"i{boyut}.png"
                ikon.png_yaz(yol, boyut)
                b = yol.read_bytes()
                self.assertEqual(b[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(b[12:16], b"IHDR")
                gen, yuk = struct.unpack(">II", b[16:24])
                self.assertEqual((gen, yuk), (boyut, boyut))

    def test_koseler_koyu_merkez_altin(self):
        self.assertLess(sum(ikon._nokta(0.01, 0.01)), 120)
        r, g, b = ikon._nokta(0.5, 0.5)
        self.assertGreater(r, 200)


if __name__ == "__main__":
    unittest.main()
