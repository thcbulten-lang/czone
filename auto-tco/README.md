# Autovergelijk op totale kosten voor een auto van de zaak

Dit is een rekenmodel plus geheugen voor de keuze van een nieuwe zakelijke auto: elektrisch, met trekhaak, ruimte voor een gezin met twee kinderen, gekozen door een DGA in Nederland. Het zet tientallen variabelen per auto, financiele constructie en gebruiksprofiel naast elkaar, rekent alles om naar een munt, en bewaart de geschiedenis van de overwegingen. De eerste vulling met auto's is een schets; elk cijfer draagt een bron en een zekerheid, en de laagste zekerheid wint.

## De vorm in een alinea

Een scenario is een auto maal een constructie bij jouw gebruik. Auto's, constructies, gebruik en fiscale spelregels staan als vier losse, leesbare bestanden in `data/`. Een klein Python-programma rekent elk scenario per jaar door en drukt alles uit in netto prive-euro's: wat de keuze jou als aandeelhouder uiteindelijk kost. Harde eisen (elektrisch, trekgewicht, zitplaatsen) filteren vooraf; een gevoeligheidsanalyse laat achteraf zien welke aannames er werkelijk toe doen. Het nulscenario is de E-klasse houden. De uitkomst is een tabel in Markdown en een zelfstandige HTML-pagina met ranglijst, kostenopbouw, verloop per jaar, gevoeligheid en alle variabelen naast elkaar. Het logboek bewaart wat we zagen en besloten; git bewaart elke eerdere stand van cijfers en conclusies.

## Waarom deze vorm en niet een spreadsheet

Een spreadsheet werkt goed voor een auto en twee constructies. Bij veertien auto's, zes constructies, drie horizonnen en tien fiscale regels met jaartallen en 60-maandsperiodes wordt elk werkblad onleesbaar en elke formule onbewijsbaar. Hier staan de regels als toetsbare functies in `tco/fiscaal.py`, met vaste gevallen in `tests/`. Verandert het belastingplan, dan verandert een getal in `data/regels.yaml` en rekent alles opnieuw. Een nieuwe auto is tien regels in `data/autos.yaml`; de matrix maakt er vanzelf drie scenario's van.

Notion of een document is prettig voor het logboek, maar te zwak voor de berekening. Daarom staat het logboek hier als tekst naast het model, en toont de HTML-pagina beide. Werken gaat via een gesprek: jij zegt wat je zag of hoorde (proefrit, prijs, trekgewicht, offerte), ik werk de bestanden bij, reken opnieuw en zet een regel in het logboek. De ranglijst verschuift, en de vorige stand blijft in git.

## De drie lagen en de spelregels

**Auto** (`data/autos.yaml`). Feiten over het voertuig. Drie prijzen doen fiscaal elk iets anders: de cataloguswaarde (nieuwprijs inclusief btw, bpm en fabrieksopties) is de basis voor bijtelling en btw-correctie, ook bij een occasion; de aanschafprijs is wat we nu betalen; de restwaarde volgt een curve per soort auto. Daarnaast massa (MRB), praktijkverbruik, accu, actieradius, trekgewicht, zitplaatsen, bagageruimte, onderhoud en banden, en vijf kwalitatieve scores (ruimte, comfort, trekervaring, merkrisico, laadsnelheid) die niet worden opgeteld maar wel naast elkaar staan.

**Constructie** (`data/constructies.yaml`). Wie koopt, wie betaalt, welke regels gelden. De BV koopt; de BV least financieel; de BV least operationeel; de BV koopt zonder privegebruik (minder dan 500 kilometer, rittenregistratie, geen bijtelling, tweede auto nodig); jij koopt prive en de BV vergoedt 0,25 per zakelijke kilometer; private lease met diezelfde vergoeding. Samengestelde scenario's met twee auto's kunnen ook, bijvoorbeeld de G9 alleen zakelijk en de E-klasse prive.

**Gebruik en situatie** (`data/profiel.yaml`). Kilometers zakelijk, prive en trekkend; laden thuis en onderweg met prijzen per kWh; salaris en tarieven; rendementseis voor geld in de BV en prive; horizon; de harde eisen. Alles wat daar ONBEKEND heet is een eerste aanname van mij.

**Spelregels** (`data/regels.yaml`). De fiscale regels voor 2026 met bron, datum en zekerheid: bijtelling (18% over de eerste 30.000 euro in 2026, 20% in 2027, 22% vanaf 2028; occasions houden het tarief van hun jaar van eerste toelating 60 maanden; youngtimers 35% over de dagwaarde), MRB (70% van het benzinetarief voor EV's tot en met 2028, 75% in 2029, vol tarief vanaf 2030; de staffel is een benadering), box 1 met afbouw van heffingskortingen, box 2, vennootschapsbelasting, Zvw, btw-correctie privegebruik (2,7% of 1,5% van de cataloguswaarde), de onbelaste kilometervergoeding (0,25 in 2026) en restwaardecurves per soort auto.

## Een munt: netto prive-euro's

Constructies schuiven kosten tussen de BV en jou prive, dus een eerlijke vergelijking heeft een gemeenschappelijke munt nodig. Een euro aftrekbare kosten in de BV kost jou als aandeelhouder uiteindelijk (1 - 19% vpb) x (1 - 24,5% box 2) = 0,61 euro netto. Een euro die je prive betaalt kost een euro. De belasting over de bijtelling is wat je werkelijk extra afdraagt bovenop je salaris: bij een DGA-loon van 58.000 euro is dat rond de 50%, omdat naast het schijftarief ook de heffingskortingen afbouwen. De kilometervergoeding is in deze munt een onbelaste uitkering uit de BV, en dat verklaart waarom prive kopen bij 15.000 zakelijke kilometers zo goed scoort. Zit het salaris op het minimum gebruikelijk loon, dan mag de bijtelling dat opvullen en kan het cash-salaris omlaag; die schakelaar staat in het profiel en in de gevoeligheidsanalyse.

## Hoe je het gebruikt

Doorrekenen: `python3 rekenen.py` in deze map (alleen PyYAML nodig). Tests: `python3 -m unittest discover -s tests`. De uitvoer staat in `uitvoer/`: `vergelijk.md` voor in git en de chat, `vergelijk.html` om te openen in een browser (werkt zonder internet), `resultaten.json` met alle details per jaar. In de HTML-pagina kies je de horizon (3, 5 of 7 jaar), filtert op constructie en type, vinkt maximaal zes scenario's aan en ziet dan de kostenopbouw, het verloop per jaar, de gevoeligheid en alle variabelen naast elkaar. Het logboek staat onderaan.

Een nieuwe auto toevoegen is een blok in `data/autos.yaml` met bron, datum en zekerheid. Een leaseofferte gaat als `lease_pm` in een scenario onder `extra` in `data/scenarios.yaml`; zonder offerte schat het model het maandbedrag en markeert dat. Een nieuwe les of een besluit is een alinea in `logboek.md` met de datum erboven.

## Wat het model bewust nog niet doet

Dit is versie 0.1. De volgende punten zijn vereenvoudigd of ontbreken, in volgorde van belang:

- Restwaardes zijn curves op gevoel, met een stevige korting voor Chinese nieuwkomers; er zijn geen harde Nederlandse cijfers gevonden. Dit is de grootste onzekerheid en de gevoeligheidsanalyse laat dat zien.
- De MRB-staffel en de provinciale opcenten zijn benaderingen; de rekenhulp van de Belastingdienst geeft het exacte bedrag per auto.
- Alle bedragen staan in euro's van vandaag, zonder indexatie van energieprijzen, tarieven of premies.
- Box 2 wordt als latente claim gerekend, ongeacht wanneer je uitkeert; de timing van dividend en de 31%-schijf blijven buiten beeld.
- Geen eigen bijdrage voor privegebruik, geen bpm, geen investeringsaftrek (KIA en MIA gelden niet voor personenauto's; een bestelauto met grijs kenteken en twee kinderen erin verliest zijn fiscale voordeel toch zodra je prive rijdt).
- Verzekering is een formule op de waarde, onderhoud en banden zijn vaste bedragen per auto.
- Laden thuis wordt zonder btw-aftrek gerekend; onderweg met aftrek voor de BV.
- Het youngtimerscenario rekent met geschatte cijfers voor de E-klasse; vul type, bouwjaar, dagwaarde, verbruik en werkelijk onderhoud in.

## Bestanden

```
auto-tco/
  README.md              dit ontwerp
  logboek.md             geschiedenis van de overwegingen
  rekenen.py             een commando: alles doorrekenen en de uitvoer schrijven
  data/regels.yaml       fiscale en economische spelregels, met bron en datum
  data/profiel.yaml      jouw situatie, gebruik, eisen
  data/autos.yaml        de auto's
  data/constructies.yaml de financiele constructies
  data/scenarios.yaml    welke combinaties we vergelijken
  tco/fiscaal.py         de regels als functies
  tco/model.py           de rekenkern per scenario en per jaar
  tco/gevoeligheid.py    wat doet een andere aanname
  tco/rapport.py         Markdown en HTML
  tests/                 vaste gevallen voor de regels
  uitvoer/               vergelijk.md, vergelijk.html, resultaten.json
```
