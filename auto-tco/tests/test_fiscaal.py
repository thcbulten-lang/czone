"""Vaste gevallen voor de fiscale regels. Draai met: python3 -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tco import fiscaal as f  # noqa: E402
from tco.laden import Invoer, lees  # noqa: E402
from tco.model import bereken_scenario  # noqa: E402

REGELS = lees("regels")
PROFIEL = lees("profiel")


def bijtelling_jaar(**kw):
    jaar = kw.pop("jaar")
    return sum(f.bijtelling_maand(REGELS, maand=(jaar, m), **kw)["bedrag"] for m in range(1, 13))


class Bijtelling(unittest.TestCase):
    def test_ev_2024_binnen_60_maanden(self):
        # 16% over 30.000 en 22% over de rest, heel 2026 binnen de periode
        b = bijtelling_jaar(jaar=2026, eerste_toelating="2024-03", aandrijving="ev", catalogusprijs=50000, dagwaarde=0)
        self.assertAlmostEqual(b, 0.16 * 30000 + 0.22 * 20000, places=2)

    def test_ev_2024_periode_loopt_af_in_2029(self):
        # periode 1-4-2024 t/m 31-3-2029; daarna het tarief van 2029 (22%)
        b = bijtelling_jaar(jaar=2029, eerste_toelating="2024-03", aandrijving="ev", catalogusprijs=50000, dagwaarde=0)
        binnen = (0.16 * 30000 + 0.22 * 20000) * 3 / 12
        buiten = 0.22 * 50000 * 9 / 12
        self.assertAlmostEqual(b, binnen + buiten, places=2)

    def test_ev_nieuw_2026(self):
        b = bijtelling_jaar(jaar=2027, eerste_toelating="2026-12", aandrijving="ev", catalogusprijs=64990, dagwaarde=0)
        self.assertAlmostEqual(b, 0.18 * 30000 + 0.22 * 34990, places=2)

    def test_ev_na_periode_volgt_jaar_tarief(self):
        # 2021-auto: periode voorbij in 2026; dan geldt het 2027-tarief in 2027 (20% over 30.000)
        b = bijtelling_jaar(jaar=2027, eerste_toelating="2021-01", aandrijving="ev", catalogusprijs=40000, dagwaarde=0)
        self.assertAlmostEqual(b, 0.20 * 30000 + 0.22 * 10000, places=2)

    def test_phev_standaard(self):
        b = bijtelling_jaar(jaar=2027, eerste_toelating="2026-12", aandrijving="phev", catalogusprijs=40000, dagwaarde=0)
        self.assertAlmostEqual(b, 0.22 * 40000, places=2)

    def test_youngtimer(self):
        b = bijtelling_jaar(jaar=2027, eerste_toelating="2008-06", aandrijving="benzine", catalogusprijs=65000, dagwaarde=8000)
        self.assertAlmostEqual(b, 0.35 * 8000, places=2)

    def test_wordt_youngtimer_halverwege(self):
        # eerste toelating juni 2012: vanaf juni 2027 ouder dan 15 jaar; auto van voor 2017 heeft 25%
        b = bijtelling_jaar(jaar=2027, eerste_toelating="2012-06", aandrijving="benzine", catalogusprijs=40000, dagwaarde=6000)
        self.assertAlmostEqual(b, 0.25 * 40000 * 5 / 12 + 0.35 * 6000 * 7 / 12, places=2)


class Overig(unittest.TestCase):
    def test_mrb_ev_korting(self):
        vol = f.mrb_jaar(REGELS, massa_ledig_kg=2000, aandrijving="benzine", provincie="Noord-Brabant", kalenderjaar=2027)
        ev = f.mrb_jaar(REGELS, massa_ledig_kg=2000, aandrijving="ev", provincie="Noord-Brabant", kalenderjaar=2027)
        self.assertAlmostEqual(ev, 0.70 * vol, places=2)
        ev30 = f.mrb_jaar(REGELS, massa_ledig_kg=2000, aandrijving="ev", provincie="Noord-Brabant", kalenderjaar=2030)
        self.assertAlmostEqual(ev30, vol, places=2)

    def test_btw_correctie(self):
        self.assertAlmostEqual(f.btw_correctie_jaar(REGELS, catalogusprijs=60000, btw_afgetrokken=True, gebruiksjaar=3), 1620.0)
        self.assertAlmostEqual(f.btw_correctie_jaar(REGELS, catalogusprijs=60000, btw_afgetrokken=True, gebruiksjaar=6), 900.0)
        self.assertAlmostEqual(f.btw_correctie_jaar(REGELS, catalogusprijs=60000, btw_afgetrokken=False, gebruiksjaar=1), 900.0)

    def test_marginaal_tarief_rond_50_procent(self):
        t = f.marginaal_tarief(REGELS, PROFIEL, 10000)
        self.assertTrue(0.45 < t < 0.56, t)

    def test_vast_tarief_overschrijft(self):
        p = dict(PROFIEL, ib_marginaal_effectief_pct=40.0)
        self.assertAlmostEqual(f.ib_over_extra(REGELS, p, 1000), 400.0)

    def test_factor(self):
        self.assertAlmostEqual(f.factor_bv_naar_prive(PROFIEL), 0.81 * 0.755, places=6)

    def test_zvw(self):
        self.assertAlmostEqual(f.zvw_werkgever_over_extra(REGELS, 58000, 10000), 610.0)
        self.assertAlmostEqual(f.zvw_werkgever_over_extra(REGELS, 75000, 10000), 0.061 * (79409 - 75000))

    def test_restwaarde_curve_volgt_leeftijd(self):
        auto = {"eerste_toelating": "2024-03", "restwaarde_curve": "ev_mainstream"}
        w = f.waarde_na(REGELS, auto, 40000, "2026-12", 12)
        self.assertTrue(0 < w < 40000)
        nieuw = {"eerste_toelating": "2026-12", "restwaarde_curve": "ev_mainstream"}
        self.assertAlmostEqual(f.waarde_na(REGELS, nieuw, 50000, "2026-12", 12), 50000 * 0.68, places=2)


class Model(unittest.TestCase):
    def test_prive_constructie_zonder_bijtelling(self):
        inv = Invoer()
        s = {"id": "t", "naam": "t", "onderdelen": [{"auto": "tesla_model_y_nieuw", "constructie": "prive_koop_kmvergoeding"}]}
        r = bereken_scenario(inv, s, 5)
        self.assertEqual(r["bijtelling_bruto_pj"], 0)
        self.assertAlmostEqual(r["lijnen_bv"]["km_vergoeding"], 0.25 * 15000, places=2)
        self.assertAlmostEqual(r["lijnen_prive"]["km_vergoeding"], -0.25 * 15000, places=2)

    def test_bv_constructie_heeft_bijtelling_en_correctie(self):
        inv = Invoer()
        s = {"id": "t", "naam": "t", "onderdelen": [{"auto": "xpeng_g9_nieuw", "constructie": "bv_koop"}]}
        r = bereken_scenario(inv, s, 5)
        self.assertGreater(r["bijtelling_bruto_pj"], 12000)
        self.assertGreater(r["lijnen_bv"]["btw_correctie"], 0)
        self.assertGreater(r["lijnen_prive"]["bijtelling_belasting"], 0)
        self.assertEqual(r["lijnen_prive"]["km_vergoeding"], 0)

    def test_filters(self):
        inv = Invoer()
        s = {"id": "t", "naam": "t", "onderdelen": [{"auto": "jaecoo_7_shs", "constructie": "bv_koop"}]}
        r = bereken_scenario(inv, s, 5)
        self.assertFalse(r["checks"]["elektrisch"])
        self.assertFalse(r["voldoet"])


if __name__ == "__main__":
    unittest.main()
