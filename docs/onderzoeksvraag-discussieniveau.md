# Onderzoeksvraag: ontbrekende labelgroep voor "discussieniveau" (object vs. metadiscussie)

Voor de argumentatie-onderzoeker achter `data/tags.toml`. Context: we zijn een kleine steekproef getagde argumenten (Tweede Kamer, stikstofdebat) handmatig aan het controleren op tag-kwaliteit, en liepen tegen een argument aan dat niet goed past in de huidige taxonomie.

## Het concrete geval

Argument (Hidde Heutink, Groep Markuszower, stikstofdebat):

> "Als wij in dit huis niet meer andere partijen mogen verwijten wat hier allemaal is misgegaan, alle partijen hier die verantwoordelijk zijn voor het slopen van de boerenstand ... Ik vind dat wij de plicht hebben om dat hier vandaag te zeggen."

Dit argument gaat niet over stikstofbeleid zelf. Het gaat over **wat er in het debat gezegd mag worden**: mag je andere partijen hier verwijten maken, is dat toegestaan binnen de spelregels van de discussie. Bij het taggen liepen we vast: de labelgroep "Dialectische Kwaliteit" (drogredenen) was niet toereikend — het is geen drogreden, het is een ander soort taalhandeling: een uitspraak *over* de discussie, niet *in* de discussie.

## Het onderliggende concept

In de argumentatietheorie (met name pragma-dialectiek, van Eemeren & Grootendorst) is dit een bekend onderscheid: **objectniveau-discussie** (over de inhoudelijke zaak) versus **metadiscussie** (discussie over de discussie zelf — de spelregels, wie mag meedoen, wat er besproken mag worden, of iets nu aan de orde is). Metadiscussie komt veel voor in politiek debat, vaak juist op emotioneel geladen momenten (orde-interrupties, "mag ik hier wel iets over zeggen", "dit hoort hier niet thuis", verwijten over verwijten maken).

We zien voorlopig (ongeverifieerd, alleen uit dit ene voorbeeld + eigen brainstorm) minstens deze varianten:
1. **Bevoegdheid** — gaat dit onderwerp/deze spreker hier wel over, wie gaat hierover ("met wie" in de zin van: wie heeft hier zeggenschap over)? Wiens taak/mandaat is dit?
2. **Agenda / tijdigheid** — is dit nu aan de orde, moeten we het er op dit moment over hebben, of is het te vroeg/te laat ("dit is nu niet het moment")?
3. **Reikwijdte** — mag dit onderwerp/deze framing hier besproken worden, of valt het buiten de scope?
4. **Vorm/setting** — moeten we het hierover hebben in déze vorm of setting (bv. wel/niet plenair, wel/niet in de commissie, wel/niet in het openbaar)?
5. **Deelnemers** — wie mag hieraan deelnemen, onder welke voorwaarden (bv. wel/niet bespreken als partij X wel/niet aanwezig is)?

Let op: "met wie" is hierboven bewust dubbel geplaatst — het kan zowel over *bevoegdheid* gaan (wie heeft hier zeggenschap/gaat hier inhoudelijk over) als over *deelnemers* (wie mag fysiek/procedureel meedoen aan dit specifieke gesprek). Of dat werkelijk twee losse dingen zijn, of dat het één en dezelfde variant is die wij ten onrechte hebben opgeknipt, is precies iets waar we jouw oordeel over willen.

Dit is een eerste eigen indeling, geen gevalideerde theorie — vandaar deze onderzoeksvraag.

## Wat we van je zouden willen weten

1. **Is dit onderscheid (object vs. metadiscussie) een aparte labelgroep waard**, of hoort dit ergens anders al thuis in de bestaande taxonomie (bv. als extra Redeneerschema, of als eigenschap van Dialectische Kwaliteit)?
2. **Klopt onze voorlopige indeling in 5 varianten** (bevoegdheid/agenda-tijdigheid/reikwijdte/vorm-setting/deelnemers), of is er een gangbaardere/preciezere indeling uit de literatuur (pragma-dialectiek of anders) die we zouden moeten overnemen?
3. **Enkelvoudig of meervoudig?** Kan een argument tegelijk over meerdere metadiscussie-aspecten gaan, of is het per uitspraak altijd één ding?
4. **Verhouding tot bestaande labelgroepen**: kan een metadiscussie-uitspraak ook nog een drogreden zijn (bv. een schijnbaar procedureel bezwaar dat feitelijk een ad hominem verhult), of sluiten "dit is metadiscussie" en "dit heeft een Dialectische-Kwaliteit-tag" elkaar per definitie uit?
5. **Sleutels + beschrijvingen** in het format van `data/tags.toml` (zie huidige structuur: `naam`/`beschrijving` per labelgroep, `sleutel`/`beschrijving` per tag), zodat we het direct kunnen overnemen.

## Waar dit terechtkomt

Als je akkoord bent met een nieuwe labelgroep, komt die in `data/tags.toml` onder het perspectief "Filosofisch & Argumentatietheoretisch" (naast "Redeneerschema" en "Dialectische Kwaliteit") en wordt hij automatisch meegenomen zodra je `data/tags.toml` aanpast — geen verdere code-actie van jou nodig.
