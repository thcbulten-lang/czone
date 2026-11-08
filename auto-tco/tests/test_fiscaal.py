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

    def test_mrb_diesel_toeslag(self):
        benzine = f.mrb_jaar(REGELS, massa_ledig_kg=2600, aandrijving="benzine", provincie="Noord-Brabant", kalenderjaar=2027)
        diesel = f.mrb_jaar(REGELS, massa_ledig_kg=2600, aandrijving="phev", provincie="Noord-Brabant", kalenderjaar=2027, brandstof="diesel")
        opc = REGELS["motorrijtuigenbelasting"]["opcenten_pct"]["Noord-Brabant"] / 100
        hoofdsom = benzine / (1 + opc)
        self.assertAlmostEqual(diesel, benzine + hoofdsom * REGELS["motorrijtuigenbelasting"]["diesel_toeslag_factor"], places=2)

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

    def test_vpb_schijven(self):
        self.assertAlmostEqual(f.vpb_bedrag(REGELS, 150000), 28500.0)
        self.assertAlmostEqual(f.vpb_bedrag(REGELS, 250000), 38000 + 0.258 * 50000)
        p = dict(PROFIEL, winst_bv_verwacht=150000)
        self.assertAlmostEqual(f.vpb_effectief_over(REGELS, p, 15000), 0.19, places=6)
        p = dict(PROFIEL, winst_bv_verwacht=250000)
        self.assertAlmostEqual(f.vpb_effectief_over(REGELS, p, 15000), 0.258, places=6)
        p = dict(PROFIEL, winst_bv_verwacht=205000)          # aftrek steekt door de schijfgrens
        self.assertAlmostEqual(f.vpb_effectief_over(REGELS, p, 15000), (5000 * 0.258 + 10000 * 0.19) / 15000, places=6)
        p = dict(PROFIEL, winst_bv_verwacht=None)
        self.assertAlmostEqual(f.vpb_effectief_over(REGELS, p, 15000), PROFIEL["vpb_pct"] / 100, places=6)

    def test_zvw(self):
        self.assertAlmostEqual(f.zvw_werkgever_over_extra(REGELS, 58000, 10000), 610.0)
        self.assertAlmostEqual(f.zvw_werkgever_over_extra(REGELS, 75000, 10000), 0.061 * (79409 - 75000))

    def test_restwaarde_curve_volgt_leeftijd(self):
        auto = {"eerste_toelating": "2024-03", "restwaarde_curve": "ev_mainstream"}
        w = f.waarde_na(REGELS, auto, 40000, "2026-12", 12)
        self.assertTrue(0 < w < 40000)
        nieuw = {"eerste_toelating": "2026-12", "restwaarde_curve": "ev_mainstream"}
        self.assertAlmostEqual(f.waarde_na(REGELS, nieuw, 50000, "2026-12", 12), 50000 * 0.68, places=2)


class Lening(unittest.TestCase):
    def test_saldo_eindigt_op_slottermijn(self):
        from tco.model import leningschema
        con = {"rente_pct": 3.0, "aanbetaling": 10000, "slottermijn": 8000, "looptijd_maanden": 48}
        l = leningschema(50000, con)
        i = 0.03 / 12
        laatste = l["saldo_per_maand"][-1]
        self.assertAlmostEqual(laatste * (1 + i) - l["maandbedrag"], 8000, places=2)
        self.assertEqual(l["hoofdsom"], 40000)
        self.assertTrue(0 < l["rente_totaal"] < 0.03 * 40000 * 4)

    def test_zonder_rente(self):
        from tco.model import leningschema
        l = leningschema(30000, {"rente_pct": 0.0, "aanbetaling": 10000, "slottermijn": 0, "looptijd_maanden": 48})
        self.assertAlmostEqual(l["maandbedrag"], 20000 / 48, places=6)
        self.assertAlmostEqual(l["rente_totaal"], 0.0)

    def test_financial_lease_goedkoper_dan_koop_bij_lage_rente(self):
        inv = Invoer()
        koop = bereken_scenario(inv, {"id": "a", "naam": "a", "onderdelen": [{"auto": "zeekr_7x_core", "constructie": "bv_koop"}]}, 4)
        fin = bereken_scenario(inv, {"id": "b", "naam": "b", "onderdelen": [{"auto": "zeekr_7x_core", "constructie": "bv_financial_lease"}]}, 4)
        self.assertLess(fin["totaal"]["netto_prive_euro"], koop["totaal"]["netto_prive_euro"])
        self.assertAlmostEqual(fin["eigen_geld_start"] - koop["eigen_geld_start"], 10000 - koop["onderdelen"][0]["basis"], places=2)


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

    def test_later_beginnend_onderdeel(self):
        inv = Invoer()
        nul = bereken_scenario(inv, {"id": "n", "naam": "n", "onderdelen": [{"auto": "e_klasse_youngtimer", "constructie": "bv_koop"}]}, 7)
        wacht = bereken_scenario(inv, {"id": "w", "naam": "w", "hoofd_auto": "zeekr_7x_core_occasion_2026", "onderdelen": [
            {"auto": "e_klasse_youngtimer", "constructie": "bv_koop", "start_jaar": 0, "jaren": 2},
            {"auto": "zeekr_7x_core_occasion_2026", "constructie": "prive_koop_kmvergoeding", "start_jaar": 2, "overrides": {"aanschafprijs": 20000}}]}, 7)
        # de eerste twee jaar zijn gelijk aan het nulscenario, daarna rijdt alleen de 7X
        for t in range(2):
            self.assertAlmostEqual(wacht["per_jaar"][t]["netto_prive_euro"], nul["per_jaar"][t]["netto_prive_euro"], places=6)
        ev = wacht["onderdelen"][1]
        self.assertFalse(ev["jaren"][0]["actief"]); self.assertFalse(ev["jaren"][1]["actief"]); self.assertTrue(ev["jaren"][2]["actief"])
        self.assertEqual(wacht["onderdelen"][0]["jaren"][2]["bv"]["energie"], 0.0)
        self.assertEqual(ev["jaren"][2]["waarde_begin"], 20000)
        self.assertEqual(wacht["auto"], "zeekr_7x_core_occasion_2026")
        self.assertTrue(wacht["voldoet"])
        self.assertEqual(wacht["eigen_geld_later"][0]["jaar"], 3)

    def test_prive_koop_met_lening_van_de_bv(self):
        inv = Invoer()
        eigen = bereken_scenario(inv, {"id": "a", "naam": "a", "onderdelen": [{"auto": "tesla_model_y_nieuw", "constructie": "prive_koop_kmvergoeding"}]}, 5)
        lening = bereken_scenario(inv, {"id": "b", "naam": "b", "onderdelen": [{"auto": "tesla_model_y_nieuw", "constructie": "prive_koop_lening_bv"}]}, 5)
        self.assertEqual(lening["bijtelling_bruto_pj"], 0)
        # rente 5% in plaats van 3% prive, en diezelfde rente komt als opbrengst bij de BV binnen
        self.assertAlmostEqual(lening["lijnen_prive"]["vermogenskosten"], eigen["lijnen_prive"]["vermogenskosten"] * 5 / 3, places=2)
        self.assertAlmostEqual(lening["lijnen_bv"]["rente_lening"], -lening["lijnen_prive"]["vermogenskosten"], places=6)
        self.assertLess(lening["eigen_geld_start"], eigen["eigen_geld_start"])

    def test_filters(self):
        inv = Invoer()
        s = {"id": "t", "naam": "t", "onderdelen": [{"auto": "jaecoo_7_shs", "constructie": "bv_koop"}]}
        streng = inv.kopie(); streng.profiel["eisen"]["elektrisch"] = True          # alleen volledig elektrisch
        r = bereken_scenario(streng, s, 5)
        self.assertFalse(r["checks"]["elektrisch"])
        self.assertFalse(r["voldoet"])
        ruim = inv.kopie(); ruim.profiel["eisen"]["elektrisch"] = "ev_of_phev"       # plug-in hybride mag ook
        self.assertTrue(bereken_scenario(ruim, s, 5)["checks"]["elektrisch"])
        benzine = {"id": "b", "naam": "b", "onderdelen": [{"auto": "skoda_kodiaq_tsi_occasion_2020", "constructie": "bv_koop"}]}
        self.assertFalse(bereken_scenario(ruim, benzine, 5)["checks"]["elektrisch"])


if __name__ == "__main__":
    unittest.main()
