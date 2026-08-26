# Design-pakket: debattenlijst als kaarten + "volgende debat"

## Doel

We faseren de huidige argumenten-tijdlijn (`ArgumentTimeline.vue`, zie
[issue #112](https://github.com/SiggyF/bipolariteit/issues/112)) uit — de
data is te sparse en te clustered op debatdagen om als continue tijdlijn een
leesbaar signaal te geven (zie "Waarom de tijdlijn wegvalt" hieronder). Het
alternatief dat we willen ontwerpen:

1. **De bestaande debattenlijst wordt een kaartenweergave.** We hebben al
   een werkende lijst (`/debatten/`, meest recente eerst, plus dezelfde
   lijst per onderwerp in `DebateList.vue`) — nu kale tekstregels
   (titel/datum/aantal argumenten). Doel is dit om te zetten naar rijkere
   kaarten: per debat een stance-verdeling (pro/contra/onduidelijk) en/of
   een topargument of -tag, in plaats van alleen een getal.
2. **Een "volgende debat"-blok bovenaan de lijst**, gevoed door de
   Kameragenda (nog geplande/lopende activiteiten — technisch dezelfde
   TK-databron als de rest van de site, alleen nog niet gebruikt voor
   toekomstige activiteiten). Dit is het belangrijkste nieuwe element: het
   laat zien dat de site live meeloopt met de Kamer, niet alleen een archief
   van afgeronde debatten is.

Het achterliggende doel van beide is een gevoel van een **actuele, levende
site** te geven, zodat bezoekers reden hebben om terug te komen — een nieuw
debat dat als kaart verschijnt (en straks: een debat dat er *aan zit te
komen*) draagt daar veel directer aan bij dan een grafiek die nauwelijks
verandert.

## Bestanden in dit pakket

- **`screenshots/debatten-lijst.png`** — de huidige, kale lijst op
  `/debatten/` (`frontend/src/pages/debatten/index.astro`). Dit is het
  hoofd-onderwerp van het herontwerp.
- **`screenshots/timeline-huidig.png`** — de huidige `ArgumentTimeline.vue`
  op een onderwerp-pagina (stikstof), zoals die nu is, om te laten zien wat
  wegvalt en waarom (zie hieronder — de staven zijn erg ongelijk gevuld,
  met lange lege stukken ertussen).
- **`screenshots/homepage.png`** — de homepage, met de bestaande
  "Uitgelicht"-kaarten (`frontend/src/pages/index.astro`, sectie
  "Uitgelicht") als referentie: dit is al een kaartenpatroon met een echt
  videostilstaand beeld per debat (via `debateThumbnailUrl()`), partij/
  spreker en titel. De nieuwe debattenkaarten mogen in dezelfde visuele
  taal, al is een thumbnail-per-kaart voor een lange lijst (~130+ debatten)
  wellicht te zwaar — aan de designer om dat af te wegen.
- **`screenshots/debat-detail.png`** — een individuele debatpagina
  (`/debatten/[id]/`), met de videospeler in actie, ter context (niet zelf
  onderwerp van dit herontwerp).
- **`screenshots/data-analyse-sparsity.png`** — een ad-hoc analyse
  (matplotlib) die de sparsity van de huidige tijdlijndata laat zien: 626
  Debatzet-taggingen, verspreid over slechts 29 dagen in een corpus van 3,5
  jaar, sterk pieken-en-dalen per debatdag. Onderbouwt waarom we van de
  tijdlijn afstappen — geen ontwerp-input, wel achtergrond.
- **`styling-tokens.md`** — dezelfde bestaande kleur-, typografie- en
  spacing-tokens als in eerdere designpakketten (licht + donker thema).

## Waarom de tijdlijn wegvalt

`ArgumentTimeline.vue` bucket't argumenten per dag en toont per bucket een
gestapelde verdeling (typologie of, recent overwogen, de nieuwe
Debatzetten-labelgroep, zie
[issue #201](https://github.com/SiggyF/bipolariteit/issues/201)). Het
probleem: argumenten komen uit Kamerdebatten en klonteren dus op een
handvol debatdagen — geen continue tijdreeks. Concreet, voor de
Debatzetten-labelgroep: 626 toekenningen op 29 dagen in 3,5 jaar corpus, de
rest van de tijdlijn leeg. Zelfs de piekdagen blijken vooral "een drukke
plenaire dag met veel sprekersbeurten" te zijn, geen inhoudelijke trend.

Omdat oudere debatten bovendien niet interessanter worden naarmate we langer
wachten (in tegendeel — recentere debatten zijn relevanter), lost meer tijd
of meer databackfill dit sparsity-probleem niet op. Een chronologische lijst
van *afzonderlijke debatten* (kaarten) past beter bij hoe de data feitelijk
is vormgegeven dan een uitgesmeerde tijdlijngrafiek.

## Bestaande implementatie (technisch, geen ontwerp)

- **`frontend/src/pages/debatten/index.astro`** — de globale lijst, alle
  debatten server-side gerenderd uit `data/export/topics/*.json` via
  `groupByDebate()` (`frontend/src/lib/groupByDebate.ts`). Eén rij per
  debat: titel, datum, aantal argumenten.
- **`frontend/src/components/DebateList.vue`** — dezelfde soort lijst,
  maar clientside en gescoped tot één onderwerp (gebruikt op de
  onderwerp-pagina). Zelfde datamodel, iets andere metadata (aantal
  sprekers i.p.v. alleen aantal argumenten).
- Een debat = één `raw_video_url` (HLS-manifest), niet één document —
  zie `frontend/src/lib/debateId.ts` voor de sleutel-afleiding en de
  toelichting waarom (één document per sprekersbeurt, gedeeld per debat).
- Per-debat stance-telling is nu nergens uitgerekend voor de lijst zelf
  (wel elders, bv. `frontend/src/lib/aggregate.ts` voor andere views) — dat
  is nieuw werk, geen bestaande waarde om simpelweg te tonen.

## Openstaande vraag: "volgende debat"-databron

Er is nog **geen pipeline-stap** die de Kameragenda (geplande/lopende
activiteiten) ophaalt — de huidige crawler verwerkt alleen debatten die al
een transcript/verslag hebben. Technisch is dit dezelfde TK OData-bron
(`Activiteit`-entiteit, zie `docs/tk-data-sources-overview.md`) met een
andere filter (status "Gepland" i.p.v. "Afgerond"), dus geen nieuwe
externe bron, wel nieuwe scope. Dit pakket gaat over hoe zo'n blok er
zou moeten uitzien (titel, datum/tijd, onderwerp indien bekend, evt.
"live nu"-status); de data-kant volgt apart.

## Tags & iconografie

Losstaand van dit pakket, maar relevant als kaarten een top-tag of
tag-badge willen tonen: `docs/design/tag-iconografie/` — `tag-styles.json`
(machine-leesbaar, incl. de huidige Debatzetten-iconen), `icons/*.svg`
(~55 iconen), en een standalone HTML-referentiedocument.

## Merk/branding

Partijlogo's: `frontend/public/party-logos/` (officiële wordmarks +
vereenvoudigde vierkante iconen, 160×160, ontwerp-klaar). Fonts zijn
self-hosted (`frontend/public/fonts/`), zie `styling-tokens.md`.

Live bekijken: `make dev`, dan naar `/debatten/` (huidige lijst) of een
onderwerp-pagina zoals `/onderwerpen/stikstof` (huidige tijdlijn, onderaan
de pagina).
