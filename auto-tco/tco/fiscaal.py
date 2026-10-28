"""De Nederlandse fiscale regels als losse, toetsbare functies.

Alle bedragen in euro. Maanden als (jaar, maand). Regels komen uit data/regels.yaml.
"""
from __future__ import annotations

import math


def parse_maand(s) -> tuple[int, int]:
    j, m = str(s).split("-")[:2]
    return int(j), int(m)


def maandindex(jm: tuple[int, int]) -> int:
    j, m = jm
    return j * 12 + (m - 1)


def maand_van_index(i: int) -> tuple[int, int]:
    return i // 12, i % 12 + 1


# ---------------------------------------------------------------- bijtelling
def _ev_korting(regels: dict, jaar: int) -> dict:
    tabel = regels["bijtelling"]["ev_per_jaar_eerste_toelating"]
    jaren = sorted(tabel)
    if jaar in tabel:
        return tabel[jaar]
    if jaar > jaren[-1]:
        return tabel[jaren[-1]]
    return {"pct": regels["bijtelling"]["standaard_pct"], "cap": 0}


def bijtelling_maand(regels: dict, *, maand: tuple[int, int], eerste_toelating: str,
                     aandrijving: str, catalogusprijs: float, dagwaarde: float) -> dict:
    """Bruto bijtelling voor een maand. Houdt rekening met de 60-maandsregel en de youngtimerregeling.

    Geeft {'bedrag', 'regime'} met regime in {'youngtimer', 'ev_korting_toelating', 'ev_korting_jaar', 'standaard'}.
    """
    b = regels["bijtelling"]
    et = parse_maand(eerste_toelating)
    idx_et = maandindex(et)
    idx = maandindex(maand)
    std = b["standaard_pct_voor_2017"] if et[0] < 2017 else b["standaard_pct"]
    leeftijd_maanden = idx - idx_et
    if leeftijd_maanden >= b["youngtimer"]["minimale_leeftijd_jaren"] * 12:
        return {"bedrag": b["youngtimer"]["pct"] / 100 * dagwaarde / 12, "regime": "youngtimer"}
    if aandrijving == "ev":
        # de 60 maanden lopen vanaf de eerste dag van de maand na de eerste toelating
        in_periode = 0 <= (idx - (idx_et + 1)) < 60
        korting = _ev_korting(regels, et[0]) if in_periode else _ev_korting(regels, maand[0])
        pct, cap = korting["pct"], korting["cap"]
        bedrag = (min(catalogusprijs, cap) * pct + max(0.0, catalogusprijs - cap) * std) / 100
        regime = "ev_korting_toelating" if in_periode else "ev_korting_jaar"
        if cap <= 0 or pct >= std:
            regime = "standaard"
        return {"bedrag": bedrag / 12, "regime": regime}
    return {"bedrag": catalogusprijs * std / 100 / 12, "regime": "standaard"}


# ---------------------------------------------------------------------- mrb
def mrb_jaar(regels: dict, *, massa_ledig_kg: float, aandrijving: str, provincie: str, kalenderjaar: int) -> float:
    """Motorrijtuigenbelasting per jaar, inclusief provinciale opcenten en EV-korting van dat jaar."""
    m = regels["motorrijtuigenbelasting"]
    massa = massa_ledig_kg + (100 if m.get("grondslag") == "rijklaar" else 0)
    st = m["staffel"]
    banden = max(0, math.ceil((massa - st["basis_kg"]) / 100))
    rijksdeel_kwartaal = st["basis_bedrag_kwartaal"] + banden * st["per_100kg_kwartaal"]
    opcenten = m["opcenten_pct"].get(provincie, 85.0) / 100
    jaar = rijksdeel_kwartaal * 4 * (1 + opcenten)
    if aandrijving == "diesel":
        jaar *= m["diesel_toeslag_factor"]
    if aandrijving == "ev":
        f = m["ev_factor_per_jaar"]
        if kalenderjaar in f:
            jaar *= f[kalenderjaar]
        elif kalenderjaar < min(f):
            jaar *= f[min(f)]
        # na het laatste jaar in de tabel: vol tarief
    return jaar


# ------------------------------------------------------- inkomstenbelasting
def ib_box1(regels: dict, inkomen: float) -> float:
    """Verschuldigde inkomstenbelasting box 1 na heffingskortingen (benadering voor een werkende zonder partner)."""
    r = regels["inkomstenbelasting_box1"]
    belasting, onder = 0.0, 0.0
    for schijf in r["schijven"]:
        tot = schijf["tot"] if schijf["tot"] is not None else float("inf")
        deel = max(0.0, min(inkomen, tot) - onder)
        belasting += deel * schijf["pct"] / 100
        onder = tot
    ahk = r["algemene_heffingskorting"]
    afbouw = ahk["maximum"] / (ahk["afbouw_tot"] - ahk["afbouw_vanaf"])
    ahk_bedrag = max(0.0, ahk["maximum"] - max(0.0, inkomen - ahk["afbouw_vanaf"]) * afbouw)
    ak = r["arbeidskorting"]
    ak_bedrag = max(0.0, ak["maximum"] - max(0.0, inkomen - ak["afbouw_vanaf"]) * ak["afbouw_pct"] / 100)
    return max(0.0, belasting - ahk_bedrag - ak_bedrag)


def ib_over_extra(regels: dict, profiel: dict, extra: float) -> float:
    """Extra inkomstenbelasting door 'extra' bovenop het salaris (bijvoorbeeld bijtelling)."""
    if extra <= 0:
        return 0.0
    vast = profiel.get("ib_marginaal_effectief_pct")
    if vast is not None:
        return extra * vast / 100
    sal = profiel["salaris_bruto"]
    return ib_box1(regels, sal + extra) - ib_box1(regels, sal)


def marginaal_tarief(regels: dict, profiel: dict, extra: float = 10000.0) -> float:
    """Effectief marginaal tarief over een extra bedrag bij het salaris, als fractie."""
    if extra <= 0:
        return 0.0
    return ib_over_extra(regels, profiel, extra) / extra


def zvw_werkgever_over_extra(regels: dict, salaris: float, extra: float) -> float:
    """Werkgeversheffing Zvw die de BV extra betaalt doordat de bijtelling het loon verhoogt."""
    z = regels["zvw"]
    cap = z["maximum_bijdrageloon"]
    return z["werkgeversheffing_pct"] / 100 * (min(salaris + extra, cap) - min(salaris, cap))


# --------------------------------------------------------------------- btw
def btw_correctie_jaar(regels: dict, *, catalogusprijs: float, btw_afgetrokken: bool, gebruiksjaar: int) -> float:
    """Btw-correctie privegebruik per vol jaar. gebruiksjaar: 1 = jaar van ingebruikname door de BV."""
    b = regels["btw"]
    hoog = btw_afgetrokken and gebruiksjaar <= b["correctie_hoog_jaren"]
    pct = b["correctie_prive_pct"] if hoog else b["correctie_prive_pct_laag"]
    return catalogusprijs * pct / 100


def ex_btw(regels: dict, bedrag: float) -> float:
    return bedrag / (1 + regels["btw"]["pct"] / 100)


# ----------------------------------------------------------- omrekenfactor
def factor_bv_naar_prive(profiel: dict) -> float:
    """Wat 1 euro aftrekbare kosten in de BV de aandeelhouder uiteindelijk netto kost."""
    return (1 - profiel["vpb_pct"] / 100) * (1 - profiel["box2_pct"] / 100)


# -------------------------------------------------------------- restwaarde
def _curve_waarde(curve: list[float], leeftijd_jaren: float) -> float:
    """Lineaire interpolatie in de curve; voorbij het einde zet de laatste verhouding door."""
    if leeftijd_jaren <= 0:
        return curve[0]
    n = len(curve) - 1
    if leeftijd_jaren >= n:
        verhouding = curve[n] / curve[n - 1]
        return curve[n] * verhouding ** (leeftijd_jaren - n)
    i = int(leeftijd_jaren)
    f = leeftijd_jaren - i
    return curve[i] + (curve[i + 1] - curve[i]) * f


def waarde_na(regels: dict, auto: dict, basis: float, startmaand: str, maanden_na_start: int) -> float:
    """Waarde van de auto 'maanden_na_start' na de startmaand, gegeven de basiswaarde bij start."""
    if "restwaarde_jaarlijks_pct" in auto:
        return basis * (auto["restwaarde_jaarlijks_pct"] / 100) ** (maanden_na_start / 12)
    curve = regels["restwaarde"]["curves"][auto["restwaarde_curve"]]
    leeftijd_start = max(0, maandindex(parse_maand(startmaand)) - maandindex(parse_maand(auto["eerste_toelating"]))) / 12
    w0 = _curve_waarde(curve, leeftijd_start)
    w1 = _curve_waarde(curve, leeftijd_start + maanden_na_start / 12)
    return basis * w1 / w0
