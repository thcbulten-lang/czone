# Carnet de Cave

Persoonlijk wijnlogboek voor op je telefoon: wijnkaarten fotograferen, flessen loggen,
een fiche technique per wijn, en advies aan tafel op basis van je eigen drinkgeschiedenis.

## Wat het is

Eén HTML-bestand (`index.html`) dat als Claude-artifact wordt gepubliceerd. Op Android open je
de link in Chrome en kies je *Toevoegen aan startscherm*; daarna gedraagt het zich als een app.
Er is geen build-stap, geen server en geen framework.

De pagina gebruikt de runtime-capabilities van het artifact-platform:

| Capability  | Gebruik                                                                 |
|-------------|-------------------------------------------------------------------------|
| `db`        | Je eigen database: collecties `wines` en `lists`. Ook door Claude uit te lezen. |
| `assets`    | Foto's van etiketten en kaarten (client-side verkleind tot max 1600 px JPEG). |
| `sample`    | Claude-aanroepen mét foto: etiket lezen, kaart uitlezen, fiche, advies. |
| `downloads` | Export van de hele database als JSON.                                   |
| `user`      | Vereist naast `db`.                                                     |

Publiceren met: `capabilities: {db:{}, user:{}, assets:{}, sample:{images:true}, downloads:true}`.

## Functies in deze basisversie

- **Vanavond**: plek invullen (restaurant + stad); alles wat je logt hangt eraan.
- **Wijnkaart fotograferen**: meerdere pagina's, per pagina leest Claude alle wijnen uit
  (producent, cuvée, appellation, jaargang, kleur, prijs per fles/glas, sectie).
- **Matching**: elke kaartregel wordt vergeleken met wat je eerder dronk (badge *gedronken · cijfer*)
  en met andere gefotografeerde kaarten (*ook bij …* met prijs). Jaargang-onafhankelijk, op
  genormaliseerde producent/naam/appellation (`wineSim`, drempel 0,6).
- **Advies**: op basis van je drinkgeschiedenis, gemiddelde cijfers per streek/kleur, de kaart,
  wat je al kent en je context (gerecht, budget). Streamt binnen en wordt bij de kaart bewaard.
- **Kaart raten**: cijfer 1-10 met één decimaal (knoppen of intypen) plus notitie; wijnen idem.
- **Fles loggen**: foto van voor- én achteretiket → velden vooringevuld, etikettekst en -feiten
  (importeur, percelen, opvoeding, zwavel, certificering) bewaard en meegegeven aan de fiche → cijfer, prijs, notities.
  Geotag en opnamemoment komen uit de EXIF van de foto (zet locatie aan in je camera-app).
  Vanuit een kaartregel kun je een fles direct loggen (velden overgenomen).
- **Spraak**: in het notitieveld de microfoon van Gboard gebruiken; de app zelf heeft geen
  microfoontoegang (het artifact-frame staat dat niet toe).
- **Fiche technique**: per wijn, met vaste kopjes (domein, terroir, vinificatie, stijl,
  serveren, aan tafel, weetjes). Onzekere feiten worden als zodanig gemarkeerd.
- **Inzichten**: aantallen, gemiddeld cijfer, per kleur, per streek, favorieten, wijnen die
  op meerdere kaarten terugkomen met prijsverschil, export.

## Datamodel

```
wines/{id}: { createdAt, producer, name, appellation, region, country, vintage, color,
              grapes[], alcohol, rating (1-10, één decimaal), price, context, placeName, city, notes,
              photo (asset-id voorkant), photoBack (asset-id achterkant),
              labelInfo {text, facts[], importer, bottler, volumeCl, certifications[], sides[]},
              geo {lat, lon}, takenAt, listId,
              fiche {text, createdAt, source, sources[{title,url}], shops[{name,url,country,vintage,price,note}], shopsAt} }
lists/{id}: { createdAt, placeName, city, geo, photos[asset-id], rating, notes,
              items[{producer, name, appellation, region, country, vintage, color, grapes[],
                     price, glassPrice, size, section, page}],
              advice, adviceAt, adviceContext }
```

## Lokaal bekijken

Open `index.html` in een browser: de interface werkt, maar zonder `window.claude` zijn
opslag en AI uitgeschakeld (de pagina toont dat). `scratch`-voorbeelddata kun je injecteren
via `window.CDC.S.wines = [...]; window.CDC.renderAll()`.

## Ideeën voor later

- Drinkvenster-herinnering: wijnen die je hoog waardeerde en die nu op dronk komen.
- Prijsvergelijking per wijn over restaurants heen (nu alleen zichtbaar bij *Komt terug op kaarten*).
- Kaart-vergelijking: welke twee restaurants hebben de meeste overlap.
- Proefnotitie-structuur (neus, mond, afdronk) als optionele velden naast vrije tekst.
- Kaartlaag met alle geotags, als de artifact-runtime ooit een kaartbibliotheek toestaat.
- Native Android-schil (Capacitor) als je microfoon en GPS rechtstreeks in de app wilt.
