"""De rekenkern: van auto x constructie x gebruik naar kosten per jaar.

Elke kostenregel heeft een betaler (bv of prive). BV-regels zijn voor vennootschapsbelasting en
omgerekend naar 'netto prive-euro's' met de factor (1 - vpb) x (1 - box 2). Prive-regels tellen een op een.
"""
from __future__ import annotations

from . import fiscaal as f

LIJNEN = ["afschrijving", "vermogenskosten", "lease", "mrb", "verzekering", "onderhoud", "banden",
          "energie", "eenmalig", "btw_correctie", "zvw", "bijtelling_belasting", "salaris_besparing", "km_vergoeding"]

GROEPEN = {
    "kapitaal": ["afschrijving", "vermogenskosten"],
    "lease": ["lease"],
    "vaste_lasten": ["mrb", "verzekering", "onderhoud", "banden"],
    "energie": ["energie"],
    "eenmalig": ["eenmalig"],
    "bijtelling": ["bijtelling_belasting", "salaris_besparing"],
    "btw_zvw": ["btw_correctie", "zvw"],
    "km_vergoeding": ["km_vergoeding"],
}
GROEP_NAMEN = {
    "kapitaal": "Afschrijving en kapitaal", "lease": "Lease", "vaste_lasten": "MRB, verzekering, onderhoud",
    "energie": "Energie", "eenmalig": "Laadpaal en trekhaak", "bijtelling": "Belasting over bijtelling",
    "btw_zvw": "Btw-correctie en Zvw", "km_vergoeding": "Kilometervergoeding",
}
ZEKERHEID_RANG = {"hoog": 3, "midden": 2, "laag": 1}


def _leeg() -> dict:
    return {k: 0.0 for k in LIJNEN}


def energiekosten(inv, auto: dict, km: dict, betaler: str) -> float:
    """Energie (stroom en/of brandstof) per jaar voor de gegeven kilometers."""
    p, r = inv.profiel, inv.regels
    kmf = p.get("km_factor", 1.0)
    km_tot = (km["zakelijk"] + km["prive"]) * kmf
    km_trek = min(km["trekkend"] * kmf, km_tot)
    ft = p["verbruik_factor_trekkend"]
    km_gewogen = (km_tot - km_trek) + km_trek * ft            # kilometers, gewogen voor trekken
    aandrijving = auto["aandrijving"]
    ev_deel = 1.0 if aandrijving == "ev" else auto.get("ev_aandeel_km", 0.0) if aandrijving == "phev" else 0.0
    kosten, btw_afgetrokken = 0.0, 0.0
    btw = 1 + r["btw"]["pct"] / 100
    if ev_deel > 0:
        laden = p["laden"]
        kwh = km_gewogen * ev_deel * auto["verbruik_praktijk_kwh_100km"] / 100 * p.get("verbruik_factor", 1.0)
        for bron, aandeel in laden["mix"].items():
            tarief = laden["prijs_per_kwh"][bron] * p.get("energieprijs_factor", 1.0)
            aftrek = betaler == "bv" and (bron != "thuis" or laden.get("btw_aftrek_thuis", False))
            kosten += aandeel * kwh * (tarief / btw if aftrek else tarief)
            if aftrek:
                btw_afgetrokken += aandeel * kwh * (tarief - tarief / btw)
    if ev_deel < 1.0:
        soort = "diesel" if aandrijving == "diesel" else "benzine"
        liter_prijs = r["energie"]["brandstofprijs_per_liter"][soort] * p.get("energieprijs_factor", 1.0)
        liters = km_gewogen * (1 - ev_deel) * auto["brandstof_l_100km"] / 100 * p.get("verbruik_factor", 1.0)
        if betaler == "bv":
            kosten += liters * liter_prijs / btw
            btw_afgetrokken += liters * (liter_prijs - liter_prijs / btw)
        else:
            kosten += liters * liter_prijs
    return kosten, btw_afgetrokken


def bereken_onderdeel(inv, onderdeel: dict, horizon: int) -> dict:
    p, r = inv.profiel, inv.regels
    auto = inv.autos[onderdeel["auto"]]
    con = inv.constructies[onderdeel["constructie"]]
    betaler = con["eigenaar"]
    bv = betaler == "bv"
    aandeel = {"zakelijk": 1.0, "prive": 1.0, "trekkend": 1.0} | (onderdeel.get("km") or {})
    km = {k: p["km_per_jaar"][k] * aandeel[k] for k in ("zakelijk", "prive", "trekkend")}
    km_totaal = (km["zakelijk"] + km["prive"]) * p.get("km_factor", 1.0)

    btw_auto = bool(auto.get("btw_auto"))
    basis = f.ex_btw(r, auto["aanschafprijs"]) if (bv and btw_auto) else float(auto["aanschafprijs"])
    cat = float(auto["catalogusprijs"])
    trekhaak_nodig = p["eisen"]["trekgewicht_geremd_min_kg"] > 0 and not auto.get("trekhaak_inbegrepen", False)
    trekhaak = auto.get("trekhaak_kosten", 0.0) if trekhaak_nodig else 0.0
    if trekhaak and auto.get("trekhaak_fabrieksoptie"):
        cat += trekhaak                                       # fabrieksoptie telt mee in de bijtelling
    laadpaal = 0.0
    if auto["aandrijving"] in ("ev", "phev") and p["laden"]["thuis_mogelijk"] and not p["laden"]["laadpaal_aanwezig"]:
        laadpaal = p["laden"]["laadpaal_kosten"]
    eenmalig_totaal = trekhaak + laadpaal
    if bv:
        eenmalig_totaal = f.ex_btw(r, eenmalig_totaal)

    operational = con.get("financiering") == "operational_lease"
    if con.get("financiering") == "financial_lease":
        a = con.get("aanbetaling_pct", 0) / 100
        rente = a * p["rendementseis_bv_pct"] + (1 - a) * con["rente_pct"]
    elif con.get("rente_pct") is not None:
        rente = con["rente_pct"]
    else:
        rente = p["rendementseis_bv_pct"] if bv else p["rendementseis_prive_pct"]
    rente /= 100
    rw_factor = p.get("restwaarde_factor", 1.0)
    start = f.maandindex(f.parse_maand(p["startmaand"]))
    salaris = p["salaris_bruto"]
    lease_pm = onderdeel.get("lease_pm")
    lease_geschat = operational and lease_pm is None

    jaren = []
    w_prev = basis
    for t in range(1, horizon + 1):
        w_t = f.waarde_na(r, auto, basis, p["startmaand"], 12 * t)
        w_t *= rw_factor                                      # gevoeligheid: restwaarde hoger of lager
        bv_l, pr_l = _leeg(), _leeg()
        eig = bv_l if bv else pr_l
        maanden = [f.maand_van_index(start + 12 * (t - 1) + i) for i in range(12)]

        eig["afschrijving"] = w_prev - w_t
        eig["vermogenskosten"] = rente * (w_prev + w_t) / 2
        eig["mrb"] = sum(f.mrb_jaar(r, massa_ledig_kg=auto["massa_ledig_kg"], aandrijving=auto["aandrijving"],
                                    provincie=p["bv_provincie"], kalenderjaar=m[0]) for m in maanden) / 12
        verz = auto.get("verzekering_pj") or max(700.0, 0.022 * w_prev * (1.21 if (bv and btw_auto) else 1.0))
        eig["verzekering"] = verz
        eig["onderhoud"] = f.ex_btw(r, auto["onderhoud_pj"]) if bv else auto["onderhoud_pj"]
        eig["banden"] = f.ex_btw(r, auto["banden_pj"]) if bv else auto["banden_pj"]
        eig["energie"], btw_energie = energiekosten(inv, auto, km, betaler)
        eig["eenmalig"] = eenmalig_totaal / horizon

        if operational:
            inbegrepen = con.get("inbegrepen", [])
            if lease_geschat:
                schatting = sum(eig[k] for k in inbegrepen if k != "vermogenskosten")
                schatting += 0.07 * (w_prev + w_t) / 2
                eig["lease"] = schatting * (1 + con.get("lease_opslag_pct", 0) / 100)
            else:
                eig["lease"] = 12 * lease_pm
            for k in inbegrepen:
                eig[k] = 0.0

        # bijtelling en wat eraan hangt
        bijtelling = 0.0
        regimes = set()
        if bv and con.get("prive_gebruik", True):
            dagwaarde = w_prev * (1 + r["btw"]["pct"] / 100) if btw_auto else w_prev
            for m in maanden:
                uit = f.bijtelling_maand(r, maand=m, eerste_toelating=auto["eerste_toelating"],
                                         aandrijving=auto["aandrijving"], catalogusprijs=cat, dagwaarde=dagwaarde)
                bijtelling += uit["bedrag"]
                regimes.add(uit["regime"])
            if p.get("bijtelling_vult_gebruikelijk_loon", False):
                # De bijtelling telt mee voor het gebruikelijk loon: het cash-salaris kan met hetzelfde bedrag omlaag.
                # Jij mist dat netto cash, de BV bespaart het bruto; de loonheffing en Zvw veranderen niet.
                pr_l["bijtelling_belasting"] = bijtelling
                bv_l["salaris_besparing"] = -bijtelling
            else:
                pr_l["bijtelling_belasting"] = f.ib_over_extra(r, p, bijtelling)
                bv_l["zvw"] = f.zvw_werkgever_over_extra(r, salaris, bijtelling)
            correctie = f.btw_correctie_jaar(r, catalogusprijs=cat, btw_afgetrokken=(btw_auto or operational), gebruiksjaar=t)
            # de correctie is nooit hoger dan de btw die dat jaar voor de auto is afgetrokken
            btw_pct = r["btw"]["pct"] / 100
            btw_afgetrokken_dit_jaar = btw_pct * (bv_l["onderhoud"] + bv_l["banden"] + bv_l["lease"] + bv_l["eenmalig"]) + btw_energie
            if t == 1 and btw_auto and not operational:
                btw_afgetrokken_dit_jaar += btw_pct * basis
            bv_l["btw_correctie"] = min(correctie, btw_afgetrokken_dit_jaar)

        if con.get("km_vergoeding") and not bv:
            vergoeding = r["km_vergoeding"]["onbelast_per_km"] * km["zakelijk"] * p.get("km_factor", 1.0)
            bv_l["km_vergoeding"] = vergoeding
            pr_l["km_vergoeding"] = -vergoeding

        jaren.append({"t": t, "kalenderjaren": sorted({m[0] for m in maanden}), "waarde_begin": w_prev, "waarde_eind": w_t,
                      "bv": bv_l, "prive": pr_l, "bijtelling_bruto": bijtelling, "regimes": sorted(regimes)})
        w_prev = w_t

    if con.get("financiering") == "financial_lease":
        eigen_geld = basis * con.get("aanbetaling_pct", 0) / 100 + eenmalig_totaal
    elif operational:
        eigen_geld = eenmalig_totaal
    else:
        eigen_geld = basis + eenmalig_totaal
    return {"auto": auto["id"], "constructie": con["id"], "betaler": betaler, "jaren": jaren, "km_per_jaar": km_totaal,
            "basis": basis, "catalogus_bijtelling": cat, "lease_geschat": lease_geschat, "eigen_geld_start": eigen_geld}


def bereken_scenario(inv, scenario: dict, horizon: int) -> dict:
    p = inv.profiel
    factor = f.factor_bv_naar_prive(p)
    vpb = p["vpb_pct"] / 100
    onderdelen = [bereken_onderdeel(inv, o, horizon) for o in scenario["onderdelen"]]
    tot_bv, tot_pr = _leeg(), _leeg()
    per_jaar = []
    for t in range(horizon):
        bv_j, pr_j = _leeg(), _leeg()
        for o in onderdelen:
            for k in LIJNEN:
                bv_j[k] += o["jaren"][t]["bv"][k]
                pr_j[k] += o["jaren"][t]["prive"][k]
        for k in LIJNEN:
            tot_bv[k] += bv_j[k]
            tot_pr[k] += pr_j[k]
        bv_som, pr_som = sum(bv_j.values()), sum(pr_j.values())
        per_jaar.append({"t": t + 1, "bv": bv_som, "prive": pr_som, "netto_prive_euro": bv_som * factor + pr_som,
                         "bijtelling_bruto": sum(o["jaren"][t]["bijtelling_bruto"] for o in onderdelen)})
    bv_som, pr_som = sum(tot_bv.values()), sum(tot_pr.values())
    netto = bv_som * factor + pr_som
    km_pj = onderdelen[0]["km_per_jaar"] if len(onderdelen) == 1 else (p["km_per_jaar"]["zakelijk"] + p["km_per_jaar"]["prive"]) * p.get("km_factor", 1.0)
    groepen = {g: sum(tot_bv[k] * factor + tot_pr[k] for k in ks) / horizon for g, ks in GROEPEN.items()}

    hoofd = inv.autos[scenario["onderdelen"][0]["auto"]]
    eisen = p["eisen"]
    checks = {
        "elektrisch": (hoofd["aandrijving"] == "ev") or not eisen["elektrisch"],
        "trekgewicht": hoofd.get("trekgewicht_geremd_kg", 0) >= eisen["trekgewicht_geremd_min_kg"],
        "zitplaatsen": hoofd.get("zitplaatsen", 0) >= eisen["zitplaatsen_min"],
    }
    zekerheid = min((inv.autos[o["auto"]].get("zekerheid", "laag") for o in scenario["onderdelen"]), key=lambda z: ZEKERHEID_RANG[z])
    return {
        "id": scenario["id"], "naam": scenario["naam"], "automatisch": scenario.get("automatisch", False),
        "notities": scenario.get("notities", ""), "horizon": horizon,
        "auto": hoofd["id"], "auto_naam": hoofd["naam"], "categorie": hoofd["categorie"],
        "constructie": scenario["onderdelen"][0]["constructie"],
        "constructie_naam": inv.constructies[scenario["onderdelen"][0]["constructie"]]["naam"],
        "onderdelen": onderdelen,
        "voldoet": all(checks.values()), "checks": checks, "zekerheid": zekerheid,
        "lease_geschat": any(o["lease_geschat"] for o in onderdelen),
        "kwalitatief": hoofd.get("kwalitatief", {}),
        "totaal": {"bv": bv_som, "bv_na_vpb": bv_som * (1 - vpb), "prive": pr_som, "netto_prive_euro": netto},
        "per_jaar_gem": {"bv": bv_som / horizon, "bv_na_vpb": bv_som * (1 - vpb) / horizon, "prive": pr_som / horizon,
                         "netto_prive_euro": netto / horizon, "per_maand": netto / horizon / 12,
                         "per_km": netto / horizon / km_pj if km_pj else 0.0},
        "lijnen_bv": {k: v / horizon for k, v in tot_bv.items()},
        "lijnen_prive": {k: v / horizon for k, v in tot_pr.items()},
        "groepen_netto_pj": groepen,
        "per_jaar": per_jaar,
        "bijtelling_bruto_pj": sum(j["bijtelling_bruto"] for j in per_jaar) / horizon,
        "eigen_geld_start": sum(o["eigen_geld_start"] for o in onderdelen),
        "km_per_jaar": km_pj,
        "factor_bv_naar_prive": factor,
    }


def bereken_alles(inv, horizon: int | None = None) -> list[dict]:
    horizon = horizon or inv.profiel["horizon_jaren"]
    uit = [bereken_scenario(inv, s, horizon) for s in inv.scenarios]
    uit.sort(key=lambda s: s["totaal"]["netto_prive_euro"])
    for i, s in enumerate(uit, 1):
        s["rang"] = i
    return uit
