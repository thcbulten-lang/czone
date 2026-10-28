"""Inlezen van de datalaag (YAML) en opbouw van de scenario's."""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

DATA = Path(__file__).resolve().parent.parent / "data"


def lees(naam: str):
    with open(DATA / f"{naam}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Invoer:
    def __init__(self, regels=None, profiel=None, autos=None, constructies=None, scenarios=None):
        self.regels = regels or lees("regels")
        self.profiel = profiel or lees("profiel")
        self.autos = {a["id"]: a for a in (autos or lees("autos"))}
        self.constructies = {c["id"]: c for c in (constructies or lees("constructies"))}
        self.scenarios = scenarios if scenarios is not None else bouw_scenarios(lees("scenarios"), self.autos, self.constructies)

    def kopie(self) -> "Invoer":
        return copy.deepcopy(self)


def bouw_scenarios(spec: dict, autos: dict, constructies: dict) -> list[dict]:
    """Zet de matrix plus de extra scenario's om in een platte lijst."""
    scenarios: list[dict] = []
    matrix = spec.get("matrix") or {}
    auto_ids = list(autos) if matrix.get("autos") in (None, "alle") else matrix["autos"]
    uitsluiten = {(u["auto"], u["constructie"]) for u in matrix.get("uitsluiten", [])}
    for aid in auto_ids:
        for cid in matrix.get("constructies", []):
            if (aid, cid) in uitsluiten:
                continue
            scenarios.append({
                "id": f"{aid}__{cid}",
                "naam": f"{autos[aid]['naam']}, {constructies[cid]['naam']}",
                "onderdelen": [{"auto": aid, "constructie": cid}],
                "automatisch": True,
            })
    for extra in spec.get("extra", []):
        s = dict(extra)
        s.setdefault("naam", " + ".join(autos[o["auto"]]["naam"] for o in s["onderdelen"]))
        s["automatisch"] = False
        scenarios.append(s)
    # het nulscenario vooraan
    scenarios.sort(key=lambda s: 0 if s["id"].startswith("nul_") else 1)
    return scenarios
