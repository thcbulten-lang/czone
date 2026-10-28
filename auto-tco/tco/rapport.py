"""Uitvoer: een Markdown-overzicht (voor git en de chat) en een zelfstandig HTML-dashboard."""
from __future__ import annotations

import json
from pathlib import Path

from .model import GROEPEN, GROEP_NAMEN

HIER = Path(__file__).resolve().parent
LOGBOEK = HIER.parent / "logboek.md"


def euro(x: float) -> str:
    s = f"{abs(x):,.0f}".replace(",", ".")
    return f"-{s}" if x < 0 else s


def _rij(s: dict) -> str:
    g = s["per_jaar_gem"]
    eisen = "ja" if s["voldoet"] else "nee (" + ", ".join(k for k, v in s["checks"].items() if not v) + ")"
    lease = " (lease geschat)" if s["lease_geschat"] else ""
    return (f"| {s['rang']} | {s['naam']}{lease} | {eisen} | {euro(g['netto_prive_euro'])} | {euro(g['per_maand'])} | "
            f"{g['per_km']:.2f} | {euro(g['bv'])} | {euro(g['prive'])} | {euro(s['bijtelling_bruto_pj'])} | "
            f"{euro(s['eigen_geld_start'])} | {s['zekerheid']} |")


KOP = ("| # | Scenario | Voldoet | Netto/jr | /mnd | /km | BV/jr voor vpb | Prive/jr | Bijtelling bruto/jr | Eigen geld start | Zekerheid |\n"
       "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|")


def schrijf_markdown(bundel: dict, pad: Path) -> None:
    p = bundel["profiel"]
    h = bundel["hoofdhorizon"]
    res = bundel["resultaten"][str(h)]
    r = [f"# Autovergelijk op totale kosten, stand {bundel['gegenereerd']}", "",
         f"Horizon {h} jaar vanaf {p['startmaand']}; {len(res)} scenario's. Alle bedragen zijn netto prive-euro's per jaar: "
         f"BV-kosten tellen voor {bundel['factor_bv_naar_prive']:.3f} (na {p['vpb_pct']}% vpb en {p['box2_pct']}% box 2), "
         f"privekosten een op een. Bijtelling belast tegen een effectief marginaal tarief van {100 * bundel['marginaal_tarief']:.1f}%.",
         "",
         f"Gebruik: {euro(p['km_per_jaar']['zakelijk'])} km zakelijk, {euro(p['km_per_jaar']['prive'])} km prive, "
         f"{euro(p['km_per_jaar']['trekkend'])} km trekkend per jaar; eis trekgewicht {euro(p['eisen']['trekgewicht_geremd_min_kg'])} kg.",
         "", "## Ranglijst", "", KOP]
    r += [_rij(s) for s in res]
    r += ["", "## Opbouw per jaar (netto prive-euro) voor scenario's die aan de eisen voldoen", "",
          "| # | Scenario | " + " | ".join(GROEP_NAMEN[g] for g in GROEPEN) + " | Totaal |",
          "|---|---|" + "---:|" * (len(GROEPEN) + 1)]
    for s in [x for x in res if x["voldoet"]][:15]:
        r.append(f"| {s['rang']} | {s['naam']} | " + " | ".join(euro(s["groepen_netto_pj"][g]) for g in GROEPEN)
                 + f" | {euro(s['per_jaar_gem']['netto_prive_euro'])} |")
    for hh, rr in bundel["resultaten"].items():
        if int(hh) == h:
            continue
        r += ["", f"## Horizon {hh} jaar (top 12)", "", KOP] + [_rij(s) for s in rr[:12]]
    r += ["", "## Gevoeligheid van de drie beste scenario's die aan de eisen voldoen", ""]
    for s in [x for x in res if x["voldoet"]][:3]:
        r += [f"**{s['naam']}** (basis {euro(s['per_jaar_gem']['netto_prive_euro'])} per jaar)", "",
              "| Variabele | Laag | Hoog | Verschil |", "|---|---:|---:|---:|"]
        for v in bundel["gevoeligheid"][s["id"]]:
            r.append(f"| {v['variabele']} | {euro(v['laag'])} | {euro(v['hoog'])} | {euro(abs(v['hoog'] - v['laag']))} |")
        r.append("")
    r += ["Elke auto draagt een zekerheid (hoog/midden/laag) en een bron in data/autos.yaml; lage zekerheid betekent: eerst verifieren, dan concluderen.", ""]
    pad.write_text("\n".join(r), encoding="utf-8")


def _slank(s: dict) -> dict:
    """Alleen wat het dashboard nodig heeft."""
    o = s["onderdelen"][0]
    j1 = o["jaren"][0]
    return {k: s[k] for k in ("id", "naam", "rang", "automatisch", "notities", "auto", "auto_naam", "categorie", "constructie",
                              "constructie_naam", "voldoet", "checks", "zekerheid", "lease_geschat", "kwalitatief", "totaal",
                              "per_jaar_gem", "groepen_netto_pj", "per_jaar", "bijtelling_bruto_pj", "eigen_geld_start",
                              "km_per_jaar", "lijnen_bv", "lijnen_prive")} | {
        "onderdelen": [{"auto": x["auto"], "constructie": x["constructie"]} for x in s["onderdelen"]],
        "mrb_pj": j1["bv"]["mrb"] + j1["prive"]["mrb"],
        "energie_pj": j1["bv"]["energie"] + j1["prive"]["energie"],
        "restwaarde_eind": o["jaren"][-1]["waarde_eind"],
        "basis": o["basis"],
        "catalogus_bijtelling": o["catalogus_bijtelling"],
        "regimes": sorted({r for j in o["jaren"] for r in j["regimes"]}),
    }


def schrijf_html(bundel: dict, pad: Path) -> None:
    data = {
        "gegenereerd": bundel["gegenereerd"], "hoofdhorizon": bundel["hoofdhorizon"], "profiel": bundel["profiel"],
        "marginaal_tarief": bundel["marginaal_tarief"], "factor_bv_naar_prive": bundel["factor_bv_naar_prive"],
        "autos": bundel["autos"], "constructies": bundel["constructies"],
        "resultaten": {h: [_slank(s) for s in rr] for h, rr in bundel["resultaten"].items()},
        "gevoeligheid": bundel["gevoeligheid"],
        "groepen": [[g, GROEP_NAMEN[g]] for g in GROEPEN],
    }
    logboek = LOGBOEK.read_text(encoding="utf-8") if LOGBOEK.exists() else "(nog geen logboek)"
    html = SJABLOON.replace("__DATA__", json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/"))
    html = html.replace("__LOGBOEK__", json.dumps(logboek, ensure_ascii=False).replace("</", "<\\/"))
    pad.write_text(html, encoding="utf-8")


SJABLOON = r"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Autovergelijk TCO</title>
<style>
:root {
  color-scheme: light;
  --bg: #f6f6f4; --surface: #fcfcfb; --surface-2: #f0efec; --line: #dddcd7; --ink: #0b0b0b; --ink-2: #52514e; --ink-3: #8a8984;
  --accent: #2a78d6; --good: #0ca30c; --critical: #d03b3b; --warning: #fab219;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4; --s6:#008300; --s7:#6250d6; --s8:#e34948;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --bg: #121211; --surface: #1a1a19; --surface-2: #262625; --line: #383835; --ink: #f0efec; --ink-2: #c3c2b7; --ink-3: #8f8e86;
    --accent: #3987e5;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #121211; --surface: #1a1a19; --surface-2: #262625; --line: #383835; --ink: #f0efec; --ink-2: #c3c2b7; --ink-3: #8f8e86;
  --accent: #3987e5;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 1280px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 24px; margin: 0 0 4px; } h2 { font-size: 17px; margin: 32px 0 10px; } h3 { font-size: 15px; margin: 18px 0 8px; }
.sub { color: var(--ink-2); margin: 0 0 12px; }
.kaart { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
.chip { background: var(--surface-2); border-radius: 999px; padding: 3px 10px; font-size: 12.5px; color: var(--ink-2); }
.chip b { color: var(--ink); font-weight: 600; }
.filters { display: flex; flex-wrap: wrap; gap: 10px 22px; align-items: center; }
.filters label { display: inline-flex; gap: 5px; align-items: center; cursor: pointer; }
.knop { border: 1px solid var(--line); background: var(--surface); color: var(--ink); border-radius: 6px; padding: 4px 10px; cursor: pointer; font: inherit; }
.knop.actief { background: var(--accent); color: #fff; border-color: var(--accent); }
.tabelwrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { padding: 6px 8px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; vertical-align: top; }
th { color: var(--ink-2); font-weight: 600; cursor: pointer; position: sticky; top: 0; background: var(--surface); }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
tr.uit td { color: var(--ink-3); }
tr.gekozen td { background: color-mix(in srgb, var(--accent) 8%, transparent); }
.stip { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }
.zek { font-size: 11px; padding: 1px 7px; border-radius: 999px; border: 1px solid var(--line); color: var(--ink-2); }
.zek.hoog { border-color: var(--good); } .zek.laag { border-color: var(--critical); }
.ok { color: var(--good); } .nee { color: var(--critical); }
svg text { font: 12px system-ui, sans-serif; fill: var(--ink-2); }
svg .as line, svg .grid line { stroke: var(--line); }
.legenda { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 6px 0 10px; font-size: 12.5px; color: var(--ink-2); }
.legenda span::before { content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; background: var(--k); vertical-align: -1px; }
#tip { position: fixed; pointer-events: none; background: var(--surface); color: var(--ink); border: 1px solid var(--line); border-radius: 6px; padding: 6px 9px; font-size: 12.5px; box-shadow: 0 4px 14px rgba(0,0,0,.12); display: none; z-index: 10; max-width: 320px; white-space: pre-line; }
.uitleg { font-size: 13px; color: var(--ink-2); }
.uitleg code { background: var(--surface-2); padding: 1px 4px; border-radius: 3px; }
.log h3 { margin-top: 20px; } .log p { margin: 6px 0; } .log ul { margin: 4px 0 8px; }
.twee { display: grid; grid-template-columns: 1fr; gap: 16px; }
@media (min-width: 960px) { .twee { grid-template-columns: 1fr 1fr; } }
.klein { font-size: 12px; color: var(--ink-3); }
select { font: inherit; padding: 3px 6px; border-radius: 6px; border: 1px solid var(--line); background: var(--surface); color: var(--ink); }
</style>
</head>
<body>
<div id="tip"></div>
<main>
<header>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">
    <div><h1>Autovergelijk op totale kosten</h1><p class="sub" id="sub"></p></div>
    <button class="knop" id="thema" type="button">Donker/licht</button>
  </div>
  <div class="chips" id="chips"></div>
  <div class="kaart uitleg" id="uitleg"></div>
</header>

<h2>Filters</h2>
<div class="kaart filters" id="filters"></div>

<h2>Ranglijst <span class="klein">(klik een kolomkop om te sorteren; vink maximaal zes scenario's aan om ze hieronder naast elkaar te zetten)</span></h2>
<div class="kaart tabelwrap"><table id="tabel"></table></div>

<h2>Waar zit het geld? <span class="klein">netto prive-euro per jaar, per kostengroep</span></h2>
<div class="kaart" id="opbouw"></div>

<div class="twee">
  <div><h2>Verloop per jaar</h2><div class="kaart" id="verloop"></div></div>
  <div><h2>Gevoeligheid <select id="gevoelig-keuze"></select></h2><div class="kaart" id="tornado"></div></div>
</div>

<h2>Alle variabelen naast elkaar</h2>
<div class="kaart tabelwrap"><table id="variabelen"></table></div>

<h2>Logboek van de overwegingen</h2>
<div class="kaart log" id="logboek"></div>
</main>
<script>
const DATA = __DATA__;
const LOGBOEK = __LOGBOEK__;
const EUR = new Intl.NumberFormat('nl-NL', {style:'currency', currency:'EUR', maximumFractionDigits:0});
const euro = x => EUR.format(Math.round(x));
const KLEUREN = ['--s1','--s2','--s3','--s4','--s5','--s6','--s7','--s8'];
const kleur = i => `var(${KLEUREN[i % 8]})`;
const state = { horizon: String(DATA.hoofdhorizon), constructies: new Set(Object.keys(DATA.constructies)),
  categorieen: new Set(), alleenVoldoet: false, sort: ['rang', 1], gekozen: [], slots: {}, gevoeligId: null };
const alleCats = new Set(); Object.values(DATA.autos).forEach(a => alleCats.add(a.categorie)); state.categorieen = new Set(alleCats);
const $ = s => document.querySelector(s);
const tip = $('#tip');
function toonTip(e, tekst) { tip.textContent = tekst; tip.style.display = 'block'; const x = Math.min(e.clientX + 14, innerWidth - 330); tip.style.left = x + 'px'; tip.style.top = (e.clientY + 14) + 'px'; }
function verbergTip() { tip.style.display = 'none'; }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

function alleScenarios() { return DATA.resultaten[state.horizon]; }
function zichtbaar() {
  return alleScenarios().filter(s => state.constructies.has(s.constructie) && state.categorieen.has(s.categorie) && (!state.alleenVoldoet || s.voldoet));
}
function gekozenScenarios() { const alle = alleScenarios(); return state.gekozen.map(id => alle.find(s => s.id === id)).filter(Boolean); }
function slotVan(id) { if (!(id in state.slots)) { const bezet = new Set(Object.values(state.slots)); let i = 0; while (bezet.has(i)) i++; state.slots[id] = i; } return state.slots[id]; }
function kies(id, aan) {
  if (aan) { if (state.gekozen.length >= 6 || state.gekozen.includes(id)) return; state.gekozen.push(id); slotVan(id); }
  else { state.gekozen = state.gekozen.filter(x => x !== id); delete state.slots[id]; }
  if (!state.gevoeligId || !state.gekozen.includes(state.gevoeligId)) state.gevoeligId = state.gekozen[0] || null;
  renderAlles();
}

function renderKop() {
  const p = DATA.profiel;
  $('#sub').textContent = `Stand ${DATA.gegenereerd}. Horizon ${state.horizon} jaar vanaf ${p.startmaand}; ${alleScenarios().length} scenario's.`;
  $('#chips').innerHTML = [
    `Zakelijk <b>${p.km_per_jaar.zakelijk.toLocaleString('nl-NL')} km</b>`, `Prive <b>${p.km_per_jaar.prive.toLocaleString('nl-NL')} km</b>`,
    `Trekkend <b>${p.km_per_jaar.trekkend.toLocaleString('nl-NL')} km</b>`, `Eis trekgewicht <b>${p.eisen.trekgewicht_geremd_min_kg.toLocaleString('nl-NL')} kg</b>`,
    `Marginaal tarief <b>${(100*DATA.marginaal_tarief).toFixed(1)}%</b>`, `1 BV-euro = <b>${DATA.factor_bv_naar_prive.toFixed(3)}</b> prive-euro`,
    `Rendementseis BV <b>${p.rendementseis_bv_pct}%</b>`, `Bijtelling vult gebruikelijk loon <b>${p.bijtelling_vult_gebruikelijk_loon ? 'ja' : 'nee'}</b>`,
  ].map(t => `<span class="chip">${t}</span>`).join('');
  $('#uitleg').innerHTML = `<b>Hoe lees je dit.</b> Elk scenario is een auto maal een financiele constructie bij jouw gebruik. Alle kosten staan in een munt: <b>netto prive-euro's per jaar</b>. Wat de BV betaalt telt voor ${DATA.factor_bv_naar_prive.toFixed(3)} (na vpb en box 2), wat jij prive betaalt telt een op een, en de belasting over de bijtelling is wat je werkelijk extra afdraagt bij jouw salaris. Het nulscenario is de E-klasse houden. Harde eisen (elektrisch, trekgewicht, zitplaatsen) staan los van de kosten: een scenario dat er niet aan voldoet staat grijs. Lage zekerheid betekent: eerst het cijfer verifieren, dan pas concluderen.`;
}

function renderFilters() {
  const f = $('#filters');
  const horizons = Object.keys(DATA.resultaten).map(h => `<button class="knop ${h === state.horizon ? 'actief' : ''}" data-h="${h}" type="button">${h} jaar</button>`).join(' ');
  const cons = Object.values(DATA.constructies).map(c => `<label><input type="checkbox" data-con="${c.id}" ${state.constructies.has(c.id) ? 'checked' : ''}> ${esc(c.naam)}</label>`).join('');
  const cats = [...alleCats].map(c => `<label><input type="checkbox" data-cat="${c}" ${state.categorieen.has(c) ? 'checked' : ''}> ${c}</label>`).join('');
  f.innerHTML = `<span>Horizon: ${horizons}</span><span>Constructie: ${cons}</span><span>Type: ${cats}</span><label><input type="checkbox" id="voldoet" ${state.alleenVoldoet ? 'checked' : ''}> alleen wat aan de eisen voldoet</label>`;
  f.querySelectorAll('[data-h]').forEach(b => b.onclick = () => { state.horizon = b.dataset.h; renderAlles(); });
  f.querySelectorAll('[data-con]').forEach(i => i.onchange = () => { i.checked ? state.constructies.add(i.dataset.con) : state.constructies.delete(i.dataset.con); renderAlles(); });
  f.querySelectorAll('[data-cat]').forEach(i => i.onchange = () => { i.checked ? state.categorieen.add(i.dataset.cat) : state.categorieen.delete(i.dataset.cat); renderAlles(); });
  $('#voldoet').onchange = e => { state.alleenVoldoet = e.target.checked; renderAlles(); };
}

const KOLOMMEN = [
  ['rang', '#', s => s.rang, true], ['naam', 'Scenario', s => s.naam, false], ['voldoet', 'Eisen', s => s.voldoet ? 1 : 0, false],
  ['zekerheid', 'Zekerheid', s => ({hoog:3,midden:2,laag:1})[s.zekerheid], false],
  ['netto', 'Netto / jaar', s => s.per_jaar_gem.netto_prive_euro, true], ['maand', '/ maand', s => s.per_jaar_gem.per_maand, true],
  ['km', '/ km', s => s.per_jaar_gem.per_km, true], ['bv', 'BV / jaar (voor vpb)', s => s.per_jaar_gem.bv, true],
  ['prive', 'Prive / jaar', s => s.per_jaar_gem.prive, true], ['bijt', 'Bijtelling bruto / jaar', s => s.bijtelling_bruto_pj, true],
  ['start', 'Eigen geld bij start', s => s.eigen_geld_start, true],
];
function renderTabel() {
  const rows = zichtbaar().slice();
  const [key, dir] = state.sort; const kol = KOLOMMEN.find(k => k[0] === key);
  rows.sort((a, b) => { const x = kol[2](a), y = kol[2](b); return (typeof x === 'string' ? x.localeCompare(y) : x - y) * dir; });
  const kop = '<tr><th></th>' + KOLOMMEN.map(k => `<th class="${k[3] ? 'n' : ''}" data-k="${k[0]}">${k[1]}${state.sort[0] === k[0] ? (dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('') + '</tr>';
  const body = rows.map(s => {
    const gekozen = state.gekozen.includes(s.id);
    const checks = Object.entries(s.checks).filter(([k, v]) => !v).map(([k]) => k).join(', ');
    const eisen = s.voldoet ? '<span class="ok">voldoet</span>' : `<span class="nee" title="niet: ${checks}">niet: ${checks}</span>`;
    const stip = gekozen ? `<span class="stip" style="background:${kleur(slotVan(s.id))}"></span>` : '';
    const g = s.per_jaar_gem;
    return `<tr class="${s.voldoet ? '' : 'uit'} ${gekozen ? 'gekozen' : ''}" data-id="${s.id}">
      <td><input type="checkbox" data-kies="${s.id}" ${gekozen ? 'checked' : ''}></td>
      <td class="n">${s.rang}</td><td>${stip}${esc(s.naam)}${s.lease_geschat ? ' <span class="klein" title="geen offerte: maandbedrag geschat">(lease geschat)</span>' : ''}</td>
      <td>${eisen}</td><td><span class="zek ${s.zekerheid}">${s.zekerheid}</span></td>
      <td class="n"><b>${euro(g.netto_prive_euro)}</b></td><td class="n">${euro(g.per_maand)}</td><td class="n">${g.per_km.toFixed(2)}</td>
      <td class="n">${euro(g.bv)}</td><td class="n">${euro(g.prive)}</td><td class="n">${euro(s.bijtelling_bruto_pj)}</td><td class="n">${euro(s.eigen_geld_start)}</td></tr>`;
  }).join('');
  const t = $('#tabel'); t.innerHTML = kop + body;
  t.querySelectorAll('th[data-k]').forEach(th => th.onclick = () => { const k = th.dataset.k; state.sort = state.sort[0] === k ? [k, -state.sort[1]] : [k, 1]; renderTabel(); });
  t.querySelectorAll('[data-kies]').forEach(i => i.onchange = () => kies(i.dataset.kies, i.checked));
}

function renderOpbouw() {
  const sc = gekozenScenarios(); const el = $('#opbouw');
  if (!sc.length) { el.innerHTML = '<p class="klein">Vink scenario\'s aan in de ranglijst.</p>'; return; }
  const groepen = DATA.groepen;
  const legenda = groepen.map(([g, n], i) => `<span style="--k:${kleur(i)}">${n}</span>`).join('');
  const W = 1000, labelB = 300, rijH = 34, pad = 12;
  let maxPos = 1, maxNeg = 0;
  sc.forEach(s => { let p = 0, n = 0; groepen.forEach(([g]) => { const v = s.groepen_netto_pj[g]; if (v >= 0) p += v; else n += -v; }); maxPos = Math.max(maxPos, p); maxNeg = Math.max(maxNeg, n); });
  const plotW = W - labelB - 90; const x0 = labelB + plotW * (maxNeg / (maxPos + maxNeg)); const sch = plotW / (maxPos + maxNeg);
  let svg = `<svg viewBox="0 0 ${W} ${sc.length * rijH + pad * 2}" width="100%" role="img" aria-label="Kostenopbouw per scenario">`;
  sc.forEach((s, r) => {
    const y = pad + r * rijH + 4, h = rijH - 10; let xp = x0, xn = x0;
    svg += `<text x="${labelB - 8}" y="${y + h / 2 + 4}" text-anchor="end">${esc(s.naam.length > 44 ? s.naam.slice(0, 43) + '…' : s.naam)}</text>`;
    groepen.forEach(([g, n], i) => {
      const v = s.groepen_netto_pj[g]; if (Math.abs(v) < 1) return; const w = Math.abs(v) * sch; let x;
      if (v >= 0) { x = xp; xp += w; } else { xn -= w; x = xn; }
      svg += `<rect x="${x + 1}" y="${y}" width="${Math.max(0, w - 2)}" height="${h}" rx="2" fill="${kleur(i)}" data-tip="${esc(s.naam)}\n${n}: ${euro(v)} per jaar"></rect>`;
      if (w > 64) svg += `<text x="${x + w / 2}" y="${y + h / 2 + 4}" text-anchor="middle" style="fill:#fff;font-size:11px;pointer-events:none">${euro(v)}</text>`;
    });
    svg += `<text x="${xp + 6}" y="${y + h / 2 + 4}" style="fill:var(--ink);font-weight:600">${euro(s.per_jaar_gem.netto_prive_euro)}</text>`;
  });
  svg += `<line x1="${x0}" y1="${pad}" x2="${x0}" y2="${sc.length * rijH + pad}" stroke="var(--ink-3)"/></svg>`;
  el.innerHTML = `<div class="legenda">${legenda}</div>${svg}<p class="klein">Segmenten links van de nullijn zijn opbrengsten (kilometervergoeding, salarisruimte). Alles in netto prive-euro's per jaar, gemiddeld over de horizon.</p>`;
  koppelTips(el);
}

function renderVerloop() {
  const sc = gekozenScenarios(); const el = $('#verloop');
  if (!sc.length) { el.innerHTML = '<p class="klein">Geen selectie.</p>'; return; }
  const H = sc[0].per_jaar.length, W = 600, Hh = 300, l = 70, r = 20, t = 16, b = 40;
  const max = Math.max(...sc.flatMap(s => s.per_jaar.map(j => j.netto_prive_euro))) * 1.1; const min = Math.min(0, ...sc.flatMap(s => s.per_jaar.map(j => j.netto_prive_euro)));
  const x = i => l + (i) * (W - l - r) / Math.max(1, H - 1); const y = v => t + (Hh - t - b) * (1 - (v - min) / (max - min));
  let svg = `<svg viewBox="0 0 ${W} ${Hh}" width="100%" role="img" aria-label="Netto kosten per jaar"><g class="grid">`;
  const stap = Math.pow(10, Math.floor(Math.log10(max))) / 2;
  for (let v = Math.ceil(min / stap) * stap; v <= max; v += stap) svg += `<line x1="${l}" x2="${W - r}" y1="${y(v)}" y2="${y(v)}"/><text x="${l - 6}" y="${y(v) + 4}" text-anchor="end">${euro(v)}</text>`;
  svg += '</g>';
  for (let i = 0; i < H; i++) svg += `<text x="${x(i)}" y="${Hh - b + 18}" text-anchor="middle">jaar ${i + 1}</text>`;
  sc.forEach(s => { const k = kleur(slotVan(s.id)); const d = s.per_jaar.map((j, i) => `${i ? 'L' : 'M'}${x(i)},${y(j.netto_prive_euro)}`).join(' ');
    svg += `<path d="${d}" fill="none" stroke="${k}" stroke-width="2"/>`;
    s.per_jaar.forEach((j, i) => svg += `<circle cx="${x(i)}" cy="${y(j.netto_prive_euro)}" r="4" fill="${k}" stroke="var(--surface)" stroke-width="2" data-tip="${esc(s.naam)}\njaar ${i + 1}: ${euro(j.netto_prive_euro)}\nbijtelling bruto: ${euro(j.bijtelling_bruto)}"></circle>`); });
  svg += '</svg>';
  const legenda = sc.map(s => `<span style="--k:${kleur(slotVan(s.id))}">${esc(s.naam.length > 40 ? s.naam.slice(0, 39) + '…' : s.naam)}</span>`).join('');
  el.innerHTML = svg + `<div class="legenda">${legenda}</div><p class="klein">Sprongen in een lijn komen uit de regels: het einde van de 60 maanden verlaagde bijtelling, de btw-correctie die na vijf jaar naar 1,5% gaat, de MRB-korting die in 2029 en 2030 afloopt.</p>`;
  koppelTips(el);
}

function renderTornado() {
  const sel = $('#gevoelig-keuze'); const sc = gekozenScenarios();
  sel.innerHTML = sc.map(s => `<option value="${s.id}" ${s.id === state.gevoeligId ? 'selected' : ''}>${esc(s.naam)}</option>`).join('');
  sel.onchange = () => { state.gevoeligId = sel.value; renderTornado(); };
  const el = $('#tornado'); const g = DATA.gevoeligheid[state.gevoeligId];
  if (!g) { el.innerHTML = '<p class="klein">Geen selectie.</p>'; return; }
  const W = 600, rijH = 30, labelB = 250, pad = 10; const basis = g[0].basis;
  const span = Math.max(1, ...g.map(v => Math.max(Math.abs(v.laag - basis), Math.abs(v.hoog - basis))));
  const mid = labelB + (W - labelB - 40) / 2, sch = (W - labelB - 40) / 2 / span;
  let svg = `<svg viewBox="0 0 ${W} ${g.length * rijH + pad * 2 + 20}" width="100%" role="img" aria-label="Gevoeligheid">`;
  g.forEach((v, i) => { const y = pad + i * rijH;
    svg += `<text x="${labelB - 8}" y="${y + 18}" text-anchor="end">${esc(v.variabele)}</text>`;
    [[v.laag, 'laag'], [v.hoog, 'hoog']].forEach(([w, lbl]) => { const d = w - basis; const x = d < 0 ? mid + d * sch : mid; const wd = Math.abs(d) * sch;
      svg += `<rect x="${x}" y="${y + 6}" width="${Math.max(1, wd)}" height="16" rx="2" fill="${lbl === 'laag' ? 'var(--s1)' : 'var(--s2)'}" data-tip="${esc(v.variabele)}\n${lbl}: ${euro(w)} per jaar (${d >= 0 ? '+' : ''}${euro(d)})"></rect>`; }); });
  svg += `<line x1="${mid}" x2="${mid}" y1="${pad}" y2="${g.length * rijH + pad}" stroke="var(--ink-3)"/><text x="${mid}" y="${g.length * rijH + pad + 16}" text-anchor="middle">basis ${euro(basis)} per jaar</text></svg>`;
  el.innerHTML = svg + `<div class="legenda"><span style="--k:var(--s1)">eerste waarde (laag)</span><span style="--k:var(--s2)">tweede waarde (hoog)</span></div><p class="klein">Hoe langer de balk, hoe meer de aanname ertoe doet. Dit is het antwoord op: welke van de tientallen variabelen verdienen onderzoek?</p>`;
  koppelTips(el);
}

function renderVariabelen() {
  const sc = gekozenScenarios(); const el = $('#variabelen');
  if (!sc.length) { el.innerHTML = ''; return; }
  const A = s => DATA.autos[s.auto], C = s => DATA.constructies[s.constructie];
  const ja = v => v ? 'ja' : 'nee';
  const rijen = [
    ['Auto', s => A(s).naam], ['Constructie', s => C(s).naam + (s.onderdelen.length > 1 ? ' + tweede auto' : '')], ['Type', s => `${A(s).categorie}, ${A(s).aandrijving}`],
    ['Nieuw of occasion', s => A(s).nieuw ? 'nieuw' : `occasion, ${(A(s).km_stand || 0).toLocaleString('nl-NL')} km`], ['Eerste toelating', s => A(s).eerste_toelating],
    ['Cataloguswaarde (basis bijtelling)', s => euro(s.catalogus_bijtelling)], ['Aanschafprijs incl. btw', s => euro(A(s).aanschafprijs)], ['Btw-auto', s => ja(A(s).btw_auto)],
    ['Bijtellingsregime', s => s.regimes.join(', ')], ['Bijtelling bruto per jaar', s => euro(s.bijtelling_bruto_pj)],
    ['Massa ledig', s => `${A(s).massa_ledig_kg} kg`], ['MRB per jaar (jaar 1)', s => euro(s.mrb_pj)], ['Accu', s => A(s).accu_kwh ? `${A(s).accu_kwh} kWh` : '-'],
    ['Actieradius WLTP', s => A(s).actieradius_wltp_km ? `${A(s).actieradius_wltp_km} km` : '-'], ['Verbruik praktijk', s => A(s).verbruik_praktijk_kwh_100km ? `${A(s).verbruik_praktijk_kwh_100km} kWh/100 km` : `${A(s).brandstof_l_100km} l/100 km`],
    ['Energie per jaar', s => euro(s.energie_pj)], ['Trekgewicht geremd', s => `${A(s).trekgewicht_geremd_kg} kg`], ['Zitplaatsen', s => A(s).zitplaatsen], ['Bagageruimte', s => A(s).bagageruimte_l ? `${A(s).bagageruimte_l} l` : '-'],
    ['Restwaardecurve', s => A(s).restwaarde_curve || `${A(s).restwaarde_jaarlijks_pct}% per jaar`], ['Waarde aan het eind', s => euro(s.restwaarde_eind)],
    ['Onderhoud + banden per jaar', s => euro(A(s).onderhoud_pj + A(s).banden_pj)], ['Eigen geld bij start', s => euro(s.eigen_geld_start)],
    ['Ruimte (1-5)', s => s.kwalitatief.ruimte], ['Comfort (1-5)', s => s.kwalitatief.comfort], ['Trekervaring (1-5)', s => s.kwalitatief.trekervaring], ['Merkrisico (5 = laag)', s => s.kwalitatief.merkrisico], ['Laadsnelheid (1-5)', s => s.kwalitatief.laadsnelheid],
    ['Zekerheid', s => s.zekerheid], ['Bron', s => A(s).bron || ''], ['Notities', s => (A(s).notities || '') + (s.notities ? ' ' + s.notities : '')],
  ];
  el.innerHTML = '<tr><th></th>' + sc.map(s => `<th><span class="stip" style="background:${kleur(slotVan(s.id))}"></span>${esc(s.naam)}</th>`).join('') + '</tr>'
    + rijen.map(([n, f]) => `<tr><td>${n}</td>` + sc.map(s => `<td style="white-space:normal;max-width:260px">${esc(f(s) ?? '')}</td>`).join('') + '</tr>').join('');
}

function renderLogboek() {
  const html = LOGBOEK.split('\n').map(l => {
    if (l.startsWith('### ')) return `<h4>${esc(l.slice(4))}</h4>`; if (l.startsWith('## ')) return `<h3>${esc(l.slice(3))}</h3>`; if (l.startsWith('# ')) return '';
    if (l.startsWith('- ')) return `<li>${esc(l.slice(2)).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')}</li>`; if (!l.trim()) return '</ul><p></p>';
    return `<p>${esc(l).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')}</p>`;
  }).join('\n').replace(/(<li>)/, '<ul>$1').replace(/<\/p>\n<li>/g, '</p>\n<ul><li>');
  $('#logboek').innerHTML = html;
}

function koppelTips(el) { el.querySelectorAll('[data-tip]').forEach(n => { n.addEventListener('mousemove', e => toonTip(e, n.dataset.tip)); n.addEventListener('mouseleave', verbergTip); }); }
function renderAlles() { renderKop(); renderFilters(); renderTabel(); renderOpbouw(); renderVerloop(); renderTornado(); renderVariabelen(); }

(function init() {
  const alle = alleScenarios();
  const start = [alle.find(s => s.id.startsWith('nul_')), ...alle.filter(s => s.voldoet).slice(0, 4)].filter(Boolean);
  start.forEach(s => { if (!state.gekozen.includes(s.id)) { state.gekozen.push(s.id); slotVan(s.id); } });
  state.gevoeligId = state.gekozen[0];
  $('#thema').onclick = () => { const r = document.documentElement; const donker = r.dataset.theme ? r.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches; r.dataset.theme = donker ? 'light' : 'dark'; };
  renderAlles(); renderLogboek();
})();
</script>
</body>
</html>
"""
