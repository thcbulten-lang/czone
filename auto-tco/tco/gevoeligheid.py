"""Gevoeligheidsanalyse: wat doet een scenario als een aanname verandert?"""
from __future__ import annotations

from .model import bereken_scenario

VARIANTEN = [
    ("Restwaarde 20% lager / hoger", {"restwaarde_factor": 0.8}, {"restwaarde_factor": 1.2}),
    ("Kilometers 25% minder / meer", {"km_factor": 0.75}, {"km_factor": 1.25}),
    ("Energieprijs 30% lager / hoger", {"energieprijs_factor": 0.7}, {"energieprijs_factor": 1.3}),
    ("Verbruik 15% lager / hoger (winter, trekken)", {"verbruik_factor": 0.85}, {"verbruik_factor": 1.15}),
    ("Marginaal IB-tarief 37,6% / 56%", {"ib_marginaal_effectief_pct": 37.56}, {"ib_marginaal_effectief_pct": 56.0}),
    ("Rendementseis BV 3% / 7%", {"rendementseis_bv_pct": 3.0}, {"rendementseis_bv_pct": 7.0}),
    ("Bijtelling vult gebruikelijk loon: nee / ja", {"bijtelling_vult_gebruikelijk_loon": False}, {"bijtelling_vult_gebruikelijk_loon": True}),
]


def analyseer(inv, scenario: dict, horizon: int) -> list[dict]:
    basis = bereken_scenario(inv, scenario, horizon)["per_jaar_gem"]["netto_prive_euro"]
    uit = []
    for naam, laag, hoog in VARIANTEN:
        waarden = []
        for override in (laag, hoog):
            kopie = inv.kopie()
            kopie.profiel.update(override)
            waarden.append(bereken_scenario(kopie, scenario, horizon)["per_jaar_gem"]["netto_prive_euro"])
        uit.append({"variabele": naam, "basis": basis, "laag": waarden[0], "hoog": waarden[1]})
    uit.sort(key=lambda v: -abs(v["hoog"] - v["laag"]))
    return uit
