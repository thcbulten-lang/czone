#!/usr/bin/env python3
"""Rekent alle scenario's door en schrijft de uitvoer (json, markdown, html).

Gebruik:  python3 rekenen.py            # alle horizonnen uit het profiel
          python3 rekenen.py --horizon 5
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tco import fiscaal
from tco.gevoeligheid import analyseer
from tco.laden import Invoer
from tco.model import bereken_alles

UIT = Path(__file__).resolve().parent / "uitvoer"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=None)
    args = ap.parse_args()
    inv = Invoer()
    horizonnen = [args.horizon] if args.horizon else inv.profiel.get("horizonnen_rapport", [inv.profiel["horizon_jaren"]])
    hoofd = args.horizon or inv.profiel["horizon_jaren"]
    resultaten = {h: bereken_alles(inv, h) for h in horizonnen}
    gevoelig = {s["id"]: analyseer(inv, next(x for x in inv.scenarios if x["id"] == s["id"]), hoofd) for s in resultaten[hoofd]}
    UIT.mkdir(exist_ok=True)
    bundel = {
        "gegenereerd": inv.regels["versie"],
        "hoofdhorizon": hoofd,
        "profiel": inv.profiel,
        "regels_versie": inv.regels["versie"],
        "marginaal_tarief": fiscaal.marginaal_tarief(inv.regels, inv.profiel),
        "factor_bv_naar_prive": fiscaal.factor_bv_naar_prive(inv.profiel),
        "autos": inv.autos,
        "constructies": inv.constructies,
        "resultaten": {str(h): r for h, r in resultaten.items()},
        "gevoeligheid": gevoelig,
    }
    (UIT / "resultaten.json").write_text(json.dumps(bundel, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    from tco.rapport import schrijf_markdown, schrijf_html
    schrijf_markdown(bundel, UIT / "vergelijk.md")
    schrijf_html(bundel, UIT / "vergelijk.html")
    print(f"{len(resultaten[hoofd])} scenario's doorgerekend voor horizon {hoofd} jaar; uitvoer in {UIT}")


if __name__ == "__main__":
    main()
