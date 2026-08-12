# Handoff — Bipolariteit MVP

Status per 2026-07-27. Zie `docs/plan.md` voor het volledige, goedgekeurde architectuurplan. Dit document is voor het vervolg: wat staat er al, wat is er onderweg ontdekt, en wat is de volgende concrete stap.

## Stand bij einde sessie (2026-08-12, validatie-experiment stijlmiddelen issue #67 + afsluiting #50) — begin hier bij een nieuwe sessie

**Issue #50** (stance/typology van Stage 1 naar Stage 1b verplaatsen) **gesloten**
met een tegenvoorstel-comment: bewijslast omgedraaid, want het bestaande
two-turn-experiment (sectie hieronder) suggereert dat classificatie-context
tijdens extractie juist kán helpen bij het herkennen van argumentgrenzen —
het omgekeerde van de aanname achter #50. Voorstel in de comment: eerst een
kleine, goedkope validatie via de bestaande ElecDeb60to20-evalharness
(`span_overlap_prf`, dezelfde 50/318-steekproef) die single-pass-extractie
vergelijkt met een variant zonder stance/typology, vóórdat dit weer wordt
opgepakt. Heropenen zodra die er is.

**Issue #67** (nieuw labelgroep "Stijlmiddelen", zie PR #68's onderzoeksrapport
`docs/Taxonomie Stijlmiddelen Politieke Debatten.md` met 10 kandidaat-tags):
kritisch doorgenomen en empirisch gevalideerd vóór opname in `data/tags.toml`.

- **Twee tags afgevallen** vóór validatie: "Dooddoener/Cliché" (te
  interpretatief, model waarschijnlijk niet sterk genoeg — zelfde soort twijfel
  als bij Slogan bleek terecht) en "Groepsidentiteit-appèl" (overlapt met de
  al bestaande `Moraliteit-Loyaliteit`-tag in Morele Fundamenten).
- **5 overgebleven kandidaten empirisch gevalideerd**: Slogan, Herhaling,
  Aangekondigde Opsomming (hernoemd van "Drieledige Opsomming" — gaat om
  vooraf een aantal aankondigen + gevolgd door precies dat aantal, niet per se
  drie), Antithese, Retorische Vraag. Nieuw, read-only experiment (geen
  DB-writes): `scripts/experiment_stijlmiddelen_validatie.py` +
  `scripts/stijlvalidatie.json` (20 fictieve testargumenten, 4 per
  stijlmiddel), branch `experiment/stijlmiddelen-validatie-issue-67`.
- **Onderweg ontdekt** (leerzamer dan de eindscore):
  1. Kale, geïsoleerde stijlmiddel-zinnen zonder onderbouwing worden door de
     extractiestap zelf al afgewezen ("geen onderbouwing = geen argument",
     `extract_argument.md`) — geen tagging-fout maar een architectuurbotsing:
     stijlmiddelen worden pas getagd ná een geslaagde extractie.
  2. Meerdere stijlmiddel-zinnen met "want..."-redenen in dezelfde paragraaf
     worden door de extractor samengevoegd tot minder/grotere argumenten
     (bedoeld gedrag: "één punt = één argument"). Fix: elk testitem in een
     eigen paragraaf.
  3. Definities zijn allesbepalend. De Slogan-definitie uit de issue-comments
     ("repeterende, herkenbare frase") is een **corpus-eigenschap**, niet op
     één los fragment te beoordelen — teruggegrepen op de brondefinitie
     (Da San Martino et al. 2019: "a brief and striking phrase ... tend to
     act as emotional appeals"). Retorische Vraag scherper gedefinieerd via
     Ad Herennium/Silva Rhetoricae: "een vraag waarvan het antwoord al
     besloten ligt in de formulering zelf" (i.p.v. "geen antwoord verwacht").
- **Eindresultaat na correcties: 20/20 correct herkend (4/4 per
  stijlmiddel)** — bevestigt dat de eerdere missers aan testopzet/definities
  lagen, niet aan het concept of het model.
- **Nog niet gedaan**: de daadwerkelijke opname in `data/tags.toml` (+
  `pipeline/taxonomy.py` `LABELGROEP_SELECTIE`, `seed_tags.py`,
  `export_tags_taxonomy.py`, iconen in `docs/design/tag-iconografie/`). Open
  vraag: onder welk perspectief — aanbeveling "Filosofisch &
  Argumentatietheoretisch" naast Dialectische Kwaliteit (retorica en
  dialectiek zijn klassiek verwante disciplines binnen argumentatietheorie),
  met een kleine herformulering van de perspectief-beschrijving.

## Stand bij einde sessie (2026-08-10, evalharnas ELECDEBATE60TO16 issue #62)

**PR #66 (branch `eval/elecdebate-harness-issue-62`) staat op WIP** — bewust
niet als "af" gemarkeerd. De onderliggende logica/databugs zijn deze sessie
echt gefixt (zie hieronder), maar de `/validatie-rapportage/<dataset>`-pagina
zelf ziet er niet uit en de resultaten zijn niet te doorgronden — dat is
zelf vastgesteld bij het bekijken van de live pagina, geen slag om de arm.
Eerste concrete vervolgstap voor een nieuwe sessie: een eigen UI/UX-ronde op
die pagina, los van de backend-logica.

Losse PR's die er ook nog liggen:
- **PR #65 (gemerged)**: bugfix `_GEEN_TAG`-sentinel in `tag_arguments.py` +
  correcte `pending_extraction`-telling in `scripts/pipeline_status.py`.
- **PR #68 (open)**: onderzoeksdocument `docs/Taxonomie Stijlmiddelen
  Politieke Debatten.md` voor issue #67 (nieuw labelgroep "Stijlmiddelen",
  ontdekt tijdens dit werk toen bleek dat "Slogan" noch drogreden noch frame
  is). Puur documentatie, geen implementatie, losstaand van #66.

### Wat er gebouwd is (PR #66, issue #62)

Evalharnas dat de extractie-/tagpipeline valideert tegen de externe
`ElecDeb60to20`-dataset (Amerikaanse presidentsverkiezingsdebatten), als
kwantitatieve aanvulling op de steekproefsgewijze experimenten op #50 (zie
de two-turn-sectie hieronder). Twee assen, onafhankelijk gescoord:
argumentherkenning (span-overlap tegen `final_relation_graph.csv`) en
2-van-de-6-drogredenen-tags (`Drogreden-Ad-Hominem`/`Drogreden-Bespelen-
Publiek` tegen `fallacy_second_version.csv` — de overige 4 vereisen een
inhoudelijk oordeel over of de redenering klopt, principieel buiten scope).
`make validate` (vars `DATASET`/`LIMIT`/`MODEL`/`BASE_URL`) maakt
cumulatieve, herhaalbare steekproeven; resultaten landen in
`data/export/eval/<dataset>.json` en op `/validatie-rapportage/<dataset>`.
Volledige methodologie en motivatie: `docs/eval-elecdebate.md`.

### Reële bugs gevonden tijdens het werk (niet alleen framing/tekst)

Ontdekt door zelf voorbeelden uit de gouden data te lezen, niet door de
scores te vertrouwen — dat bleek herhaaldelijk nodig:

1. **Claim+premisse werden niet samengevoegd.** `scripts/convert_elecdebate.py`
   voegde de twee helften van een Support-relatie als losse spans toe i.p.v.
   als één argument-eenheid, met kale stellingnames en losse onderbouwingen
   zonder claim als resultaat — precies wat onze eigen extractieprompt zou
   afwijzen. Gefixt: groeperen op (sprekersbeurt, Governor-tekst), min-start/
   max-end samenvoegen. 999 → 627 argument-spans.
2. **Geneste dubbele drogreden-annotaties** (dezelfde fallacie op twee
   granulariteiten in de brondata, bv. een volledige twee-zinsuiting én een
   losse rij voor alleen de tweede zin) werden niet gededupliceerd.
   `_drop_nested_fallacies()` toegevoegd. 336 → 324 drogreden-citaten.
3. **Tagprompt kreeg geen context bij korte citaten.** Een deel van de
   gouden drogreden-citaten is maar één woord ("Loaded Language"-stijl
   annotatie in de brondataset, bv. "disaster", "stolen"). Die kaal aan de
   tagprompt geven (`quote_context=None`) is geen eerlijke test. Gefixt
   (`_context_window`, ±200 tekens rond het citaat). Op een verse 10-record
   qwen-steekproef: drogreden-tag-recall 0.00 → 0.25, F1 0.00 → 0.40.
4. **Prompt-instructies waren zelf misleidend**: beweerde "Tweede Kamer-debat"
   (feitelijk onjuist voor deze dataset — `_build_prompt()` kreeg een
   `debate_context`-parameter, default blijft "Tweede Kamer-debat" voor
   productie), en vroeg het model om zelf een pro/contra-as per argument af
   te leiden voor een veld dat de eval niet eens scoort. Nu: stance staat
   altijd op `"unclear"`.
5. **"Span"-terminologie lekte in de tagging-taal** terwijl tagging geen
   eigen spandetectie doet (het classificeert een compleet citaat, net als
   `tag_arguments.py` in productie) — hernoemd naar "citaten" waar van
   toepassing.

### Volgende stap

UI/UX-ronde op `/validatie-rapportage/<dataset>` (leesbaarheid, layout,
hoe voorbeelden gepresenteerd worden) — de backend/databugs zijn opgelost,
de pagina zelf niet. Daarna: grotere `make validate`-steekproef (nu maar
10/318 records) voor een betrouwbaarder beeld, en uitzoeken waarom
`qwen/qwen3.6-27b` op een eerder moment deze sessie consistent lege
completions gaf (leek een lokale LM Studio-model-state-kwestie, niet
gereproduceerd na herladen).

## Stand bij einde sessie (2026-08-10, two-turn-tagging-experiment voor issue #50)

Voordat issue #50 ("stance/typology loskoppelen van Stage 1 naar Stage 1b")
daadwerkelijk gebouwd werd, eerst getest of extractie+tagging als twee turns
binnen één LM Studio-sessie (messages-array met turn-1-antwoord als
voorgeschiedenis) sneller is dan de huidige aanpak, in de hoop dat de
brontekst-context "warm" zou blijven en niet opnieuw geprocessed hoeft te
worden. Volledig uitgeschreven in nieuw `docs/two-turn-tagging-experiment.md`.
Kort: **verworpen** — op 10 testdocumenten (topic `stikstof`) was de
two-turn-aanpak gemiddeld ~2,5x langzamer dan de bestaande single-call
baseline (geen aanwijzing voor prefix-caching-winst; turn 2 was steevast de
traagste stap), én leverde het een kwaliteitsregressie op de argumentgrenzen
zelf op (andere opknipping/hallucinatie zodra stance/typology-framing uit
turn 1 werd weggelaten). Issue #50's oorspronkelijke doel (goedkope
hertagging zonder herextractie) blijft overeind, maar dan via de
oorspronkelijk voorgestelde route van twee écht onafhankelijke
stages/prompts, niet via sessie-chaining voor snelheidswinst. Experiment-
artefact `scripts/experiment_two_turn_tagging.py` blijft in de repo als
referentie, niet in productie gebruikt. Geen schema-, pipeline- of
prompt-wijzigingen; issue #50 zelf staat nog open.

## Stand bij einde sessie (2026-08-04, derde topic: asiel) — begin hier bij een nieuwe sessie

Branch `topic-asiel`, nog geen PR. Doel was een derde onderwerp opzetten met de resterende Gemini-credits. Het onderwerp staat er (crawl, ingest, omschrijving, export), maar de **extractie is bewust teruggedraaid en moet opnieuw** — zie "Wat er nog moet".

### Het onderwerp zelf

`asiel` ("Asiel en migratie"), topic-id 3. Gecrawld op twee trefwoorden (`asiel`, `migratie`) over vijf debatsoorten: Plenair debat (debat/wetgeving/tweeminutendebat), Commissiedebat, Wetgevingsoverleg. Plus 100 plenaire dagverslagen via `-a topic=Vragenuur -a soort=Vragenuur`, want vragenuur-activiteiten heten in de brondata letterlijk "Vragenuur" en matchen dus nooit op een inhoudelijk trefwoord.

Ingest: `--topic asiel --also-dir migratie --also-dir Vragenuur --also-keyword migratie`. Die laatste optie is nieuw (zie hieronder). Corpus na opschoning: **5.703 documenten binnen de cutoff**, na verwijdering van 1.238 arbeidsmigratie-documenten, 862 ICT-migratiedocumenten en het markeren van 5.154 voorzitter-beurten.

### Wat er is geleerd over de pro/contra-as (het echte werk van deze sessie)

Een eerste extractie van 267 argumenten legde drie structurele problemen bloot:

1. **De as stond verkeerd om.** PRO was "beperking van de instroom" gezet; besloten is PRO = *bescherming van de asielzoeker*. De tiebreak-regel is: bij een willekeurige keuze noemen we de pool die het dichtst bij het huidige kabinetsbeleid ligt PRO — maar **die regel hoort niet in `topics.description`**, want dan gaat de LLM "steunt dit het kabinet?" afwegen in plaats van de inhoud.
2. **Een mechanische omdraaiing (`pro` <-> `contra`) repareert dat niet.** De toenmalige prompt bevatte de regel "kritiek op het huidige/voorgestelde beleid is contra". Bij asiel wordt het kabinet van twee kanten bekritiseerd (te ver, of niet ver genoeg), dus een deel van de labels was via die vuistregel toegekend en niet via de as. Omdraaien maakt zulke labels zelfstandig fout in plaats van herkenbaar raar. Geverifieerd aan een steekproef: een PVV-uitspraak "is de wet wel streng genoeg?" stond na de omdraaiing als PRO.
3. **Het corpus was te smal**: 145 van de 267 argumenten kwamen uit één wetsbehandeling (dwangsommen bij niet tijdig beslissen), omdat batches op `documents.id` lopen en dat debat het laagste id-bereik had. Gevolg: gezinshereniging 1 argument, terugkeer 6, tweestatusstelsel 3.

De gebruiker heeft de 267 argumenten daarom zelf gewist (arguments + claims + tags, en `extraction_attempted_at` teruggezet).

### Wijzigingen in de pipeline

- **`--also-keyword`** in `ingest_tk.py`: verbreedt waaróp gematcht wordt, naast `--also-dir` dat verbreedt wélke mappen gescand worden. Zonder dit levert een puur migratiedebat uit de migratie-map nul sprekerbeurten op.
- **Voorzitter-detectie op tekst**: de `<activiteitdeel><titel>`-heuristiek mist voorzitter-beurten bij commissiedebatten; content die met "De voorzitter:" begint telt nu ook. Dat markeerde 5.154 documenten over alle topics heen (asiel 3.418, stikstof 1.475, abortus 261), zonder verlies van bestaande argumenten (nul argumenten kwamen uit zulke beurten).
- **Vierde standpunt `ander_onderwerp`** plus kolom `arguments.ander_onderwerp` (welk onderwerp het wél is). Migratie: `scripts/migrate_stance_ander_onderwerp.py` (tabelherbouw, want SQLite kan een CHECK niet wijzigen). Deze argumenten vallen uit de export; `status.json` toont aantal + top-10 onderwerpen. De frontend blijft dus op drie standpunten.
- **Promptwijzigingen** in `extract_argument.md`: standpunt volgt de pool die de onderbouwing steunt (niet regering-vs-oppositie), onderbouwing zonder pool is `unclear`, uitspraken over de behandeling van een voorstel (stemgedrag, moties-appreciatie, debatverzoeken) leveren geen argument op, en de `ander_onderwerp`-instructie. Terminologie volgt bewust de about-pagina: *standpunt* en *onderbouwing*.

### Vier bugs onderweg gevonden en gerepareerd

1. `scripts/agy_run_extraction_batch.py` gooide `UnboundLocalError` op het eerste document van elke run (tellers niet geïnitialiseerd sinds commit `6775fa5`) — `make extract-agy` was dus volledig stuk.
2. De crawler vroeg `$top = limit * 3`; boven 250 antwoordt de TK-API met HTTP 400 en laat Scrapy die respons stil vallen. Elke `-a limit=` boven 83 leverde dus geruisloos nul resultaten. Nu begrensd op `odata.MAX_TOP`.
3. `vergadering_soort_for_activiteit` gokte "Commissie" voor "Vragenuur", dat plenair is — vragenuur was daardoor onvindbaar.
4. `scripts/backfill_voorzitter_turns.py` pakte de tuple van `find_matching_activiteiten` niet uit (stuk sinds `title_match` erbij kwam).

### Quota-ervaring (agy/Gemini)

Bevestigt de eerdere kalibratie: **~0,1% dagquotum per document**, ~5-9s per call, ~6 documenten/minuut. `/usage` blijft alleen interactief uitleesbaar. Deze sessie verbruikt: ~37% (100% → 63%), waarvan een flink deel aan de teruggedraaide extractie.

### Wat er nog moet

1. **Extractie opnieuw draaien** met de nieuwe prompt en omschrijving, en **niet vanaf het laagste id**: de eerste 48 documenten van de nieuwe run leverden 39 argumenten op waarvan **32 `ander_onderwerp`** (arbeidsmigratie 14, faunabeheer/wolf 7, ruimtelijke ordening 3). Dat is de staart van losse beurten waarin "migratie" toevallig valt. Begin bij een echt asieldebat: `make extract-agy TOPIC=asiel LIMIT=300 MIN_ID=6542` (6542 = "Begroting Asiel en Migratie 2025"; 7860 = "Vreemdelingen- en asielbeleid"; 9213 = "Asielnoodmaatregelenwet en tweestatusstelsel"). `MIN_ID` is deze sessie aan het make-target toegevoegd. Een titelfilter is bewust *niet* toegevoegd.
2. **Taggen** (`make tag-agy TOPIC=asiel`) — maar pas als de labels definitief zijn; bij een herextractie verdwijnen argumenten en dus hun tags.
3. **Openstaand van vóór deze sessie**: 179 ongetagde abortus-argumenten, 206 ongetagde stikstof-argumenten.
4. **Issue [#50](https://github.com/SiggyF/bipolariteit/issues/50)**: stance en typologie verplaatsen van Stage 1 naar Stage 1b, zodat een as-correctie voortaan een hertagging is in plaats van een volledige herextractie. Dit is precies wat deze sessie duur maakte.
5. De teaser in `frontend/src/lib/topics.ts` staat er al; `data/export/topics/asiel.json` bestaat maar is momenteel leeg (0 argumenten).

## Stand bij einde sessie (2026-07-30, releasepad)

Losse sessie, eigen branch (`feature/preview-release`, PR [#15](https://github.com/SiggyF/bipolariteit/pull/15)). Ging alleen over publiceren; niets aan de pipeline of de kaart veranderd. Volledige documentatie staat in **`docs/release.md`** — hieronder alleen wat je daar niet uit afleidt.

Releasen is: `make export` → commit → `git tag v0.3.0` → `git push origin v0.3.0`. De Action doet de rest. `v0.3.0` wordt `https://v0-3-0-preview.bipolariteit.org`.

**Waarom Workers en niet Pages.** Eerst op Cloudflare Pages ingezet, maar Pages ondersteunt geen custom domain per preview-deployment — er is geen wildcard voor branch-aliassen. Workers static assets wel; `custom_domain: true` regelt DNS-record en certificaat vanzelf. Gevolg: `_headers` werkt niet (Pages-feature, wordt op Workers stil als statisch bestand geserveerd), vandaar de noindex-header in `deploy/worker.js`.

**Waarom `-preview` een streepje is en geen punt.** Universal SSL is gratis maar dekt één niveau: `*.bipolariteit.org`. Twee niveaus diep zou een betaald Advanced Certificate vereisen.

**De ontwikkelbalk is fail-open.** Verschijnt tenzij `PUBLIC_RELEASE_OFFICIEEL=true`. Belangrijk detail: `PUBLIC_RELEASE_TAG` moet mee met `npm run build`, niet met het deploy-script — Astro bakt de balk in de HTML. Daarom bouwen de `release`-targets zelf in plaats van `build` als prerequisite te gebruiken. Zet je de vlag op de verkeerde plek, dan is de balk leeg zonder dat er iets faalt.

**Al gedaan door de gebruiker:** Cloudflare API-token aangemaakt (sjabloon *Edit Cloudflare Workers* plus Zone→DNS→Edit en Zone→SSL and Certificates→Edit) en samen met het account-ID als GitHub-secret gezet. Het per ongeluk aangemaakte Pages-project `bipolariteit` is weer verwijderd.

**Nog niet gedaan:** er is nog nooit echt gedeployd. De eerste tag is de eerste live test; als hij stukloopt op een 403 gaat het vrijwel zeker om een ontbrekend token-recht — zie de hersteltip in `docs/release.md`, en maak géén nieuwe token aan.

**Losse constatering:** er stond een `astro dev`-server uit een vorige sessie op poort 4321, waardoor `make test-frontend` stil tegen de verkeerde server praatte en op een timeout viel. `make dev-stop` loste het op. De moeite waard om te onthouden bij een onverklaarbare smoke-test-fout.

## Stand bij einde sessie (2026-07-30, vervolg)

Vervolg op de sessie hieronder, zelfde dag, zelfde branch (`feature/correspondentie-3d`, PR [#8](https://github.com/SiggyF/bipolariteit/pull/8)). Deze sessie ging over ontwerpersfeedback op de kaart uit de vorige sessie, plus een reeks navigatiebugs die tijdens het verifiëren aan het licht kwamen. **Alles is gecommit** (twee commits: de feature, plus een opruimronde erna).

### Ontwerpersfeedback verwerkt

- **Tagpunten zijn nu effen, halftransparante cirkels, geen iconen meer.** Zowel de per-tag-iconen (vijftig) als later ook de per-perspectief-iconen (vier) bleken op kaartschaal niet als teken te lezen, vooral in dichte clusters van hetzelfde perspectief — zie de "brain"-blob die de sessie in gang zette (screenshot toonde een cauliflower-vormige klont in plaats van een herkenbaar brein-icoon; bleek 3-4 overlappende iconen van dezelfde vorm, geen renderbug). Kleur draagt de codering nu alleen; `tag-styles.json`'s `marker`-veld (circle/triangle/diamond/square) ligt klaar als extra onderscheid mocht kleur ooit weer te weinig zijn.
- **Iconen komen niet meer uit een gok naar het gelijknamige Lucide-icoon.** De gebruiker leverde de échte SVG's uit het ontwerpsysteem aan (eerst als `<script>`-blok met inline paden, uiteindelijk verwerkt tot `docs/design/tag-iconografie/icons/*.svg`, één bestand per icoonnaam). `build_tag_icons.mjs` leest daar nu uit i.p.v. uit `lucide-static` (dependency verwijderd) — geen `VERVANGERS`-tabel met handmatige gok meer nodig, want alle 54 namen uit `tag-styles.json` hebben nu hun eigen tekening.
- **Partijlogo's**: vereenvoudigde iconenset (`frontend/public/party-logos/simplified/*.svg`, vierkant 160×160, door de ontwerper geleverd) i.p.v. de officiële wordmarks met outline-effect. Vast op 20% verzadiging (geen toggle meer, "in kleur" verloor het altijd). Rijen zonder partij (of zonder logobestand) krijgen een initiaal-tegel i.p.v. een kale stip, dezelfde stijl als `PartyLogo.vue`'s bestaande placeholder — nu gedeelde `partyInitial()`-logica in `parties.ts`.
- **Plotcontrols herbouwd als pil-toolbar** (bordered, mono/uppercase labels) i.p.v. native `<select>`/checkbox, consistent met de rest van de paper-stijl. 2D/3D is nu ook een toggle i.p.v. checkbox.
- **Default rij-eenheid is nu "Personen"** i.p.v. "Partijen" — een partij is een optelsom van tientallen sprekers, en die nuance is precies waar de kaart voor bedoeld is.

**Nog een losse constatering, niet opgevolgd:** het `logos.ai`-bestand (Illustrator-bronbestand voor de partijlogo's) staat als los, ongetrackt/gewijzigd bestand in de repo; gebruiker vroeg expliciet om het mee te pushen, dus zit in de tweede commit.

### Drie echte navigatiebugs gevonden tijdens het verifiëren

1. **Scrollen op de 2D-kaart scrollde de pagina, niet de grafiek.** `wiel()` deed alleen `preventDefault()` in de 3D-tak; in 2D liet dat de pagina onder de muis vandaan scrollen, waardoor de rest van de scrollbeweging de kaart al niet meer raakte. `preventDefault()` staat nu onvoorwaardelijk vooraan in de functie.
2. **Zoom kon niet ver genoeg uit.** De 2D-assen hadden geen vaste `min`/`max` (auto-schaal), dus het genormaliseerde standaardvenster (90e-percentielvenster tegen de Ideologie-Links-Economisch-uitschieter) werd zelf de 0%-100%-referentie voor `dataZoom` — er was letterlijk nergens heen om uit te zoomen. Nieuwe `asVolledigeGrenzen` (het echte maximum, niet het percentiel) is nu de vaste asgrens; `asGrenzen` (90e percentiel) blijft alleen het *startvenster*.
3. **Dat startvenster zette zichzelf niet betrouwbaar terug.** `dispatchAction` op de ECharts-instantie bleek racy (chartRef wordt al waar vóórdat VChart's eigen `onMounted` de instantie initialiseert) — zelfs met een `requestAnimationFrame`-herkansing bleef het een stille no-op. Nu declaratief: `forceerNormalisatie` (ref) bepaalt of `chartOption` zelf `startValue`/`endValue` meegeeft in de `dataZoom`-config, in dezelfde `setOption`-aanroep die de kaart toch al ververst. Gaat na die ene toepassing weer uit (watcher op `chartOption`, `flush: "post"`) zodat latere her-renders (bv. een tagklik) de handmatige zoomstand van de gebruiker niet resetten.

Bijvangst: labels in 2D bleven bij inzoomen vast op de globale top-12-op-frequentie, ook als die twaalf allemaal buiten het gezoomde venster vielen. Nu bijgehouden via het `datazoom`-event (`opDataZoom`/`zicht2D`) — analoog aan de al bestaande dieptegebaseerde labelselectie in 3D tijdens slepen.

### Radiale compressie tegen de Ideologie-Links-Economisch-uitschieter

Op verzoek gecheckt: de Mahalanobis-afstand van deze tag (n=43, de zeldzaamste) in de eerste 3 CA-componenten is **~6× de mediaan** — geen renderbug maar standaard CA-gedrag bij een kolom met kleine massa. Na overleg (opties besproken: laten staan, radiale compressie, clip+flag, hogere ondergrenzen) gekozen voor radiale compressie: `r' = r^0.6` op de weergavecoördinaten, richting ongewijzigd, toegepast ná de echte CA en ná `alignSigns` (nieuwe `weergave`-computed, puur presentatie — `correspondence` zelf blijft ongemoeid, en klikken-om-te-filteren gaat toch op tagsleutel/rijlabel). Effect: de uitschieter zakt naar ~2,9× de mediaan, én — neveneffect van `r^p > r` zodra `r < 1` — de dichte kern van de wolk spreidt juist uit, waar het echte overlapprobleem zat.

**Open punt:** afstanden op de kaart zijn na deze compressie geen letterlijke chi-kwadraatafstanden meer, alleen richting en relatieve volgorde blijven behouden. Dat staat nu alleen in code-comments, nog niet in de gebruikersgerichte panel-copy of `/about`.

### Nog niet gedaan

- dim1/dim2/dim3 een naam (x/y/z) en eenheid geven in de UI — gevraagd, nog niet opgepakt.
- 3D-panning (naast roteren en zoomen) — gevraagd, nog niet opgepakt.
- Het palet-hervalidatie-punt uit de vorige sessie (zie hieronder) staat nog open.

## Stand bij einde sessie (2026-07-30) — verouderd, zie sectie hierboven

Deze sessie ging volledig over de correspondentiekaart (`frontend/src/components/TagCorrespondenceMap.vue`), issue #3. Branch: `feature/correspondentie-3d`. **Alles staat uncommitted** — `npm test` (23 tests) en `npx astro build` zijn groen, de kaart is met Playwright-screenshots geverifieerd, maar er is bewust nog niet gecommit.

### De drie gemelde 3D-bugs, en wat de oorzaak was

De 3D-modus is geen `echarts-gl`/`scatter3D`, maar een eigen orthografische-projectie-laag vóór een gewone 2D-scatter. Dat is een bewuste keuze (zie de comment bovenin de component: klikken-om-te-filteren, tooltip, dimmen en labelplaatsing hoeven niet dubbel gebouwd te worden), en het heeft één concreet voordeel dat onderweg belangrijk bleek: `labelLayout` is een 2D-cartesische feature die `scatter3D` niet kent, en die hebben we hier dus wél.

1. **Assen liepen niet synchroon met de punten.** Twee oorzaken. (a) x- en y-as spanden allebei `±grens` over een tekengebied van 3:1, dus op het scherm was de projectie een rotatie *plus* een uitrekking — de aslijnen bleven bijna horizontaal terwijl de wolk kantelde. Nu is het venster gelijk-aspect: een `ResizeObserver` op de wrapper meet de verhouding en `grensX` volgt daaruit. (b) Het venster werd elk frame opnieuw uit de *geprojecteerde* punten berekend, dus de kaart zoomde bij elke muisbeweging in en uit. Het venster hangt nu aan `straal`, een rotatie-invariante maat.
2. **Vertraging tussen slepen en punten.** ECharts koppelt zijn overgangsanimatie aan de index in de data-array, en de dieptesortering hersorteert die array elk frame — punten animeerden dus naar de plek van hun buurman. `animation: false`. (Dit is de 2D-scatter-knop `series.animation`, niet `scatter3D.animationDurationUpdate`.)
3. **Geen assenraster.** In 3D stond het cartesische raster van ECharts bewust uit (het zou een gedraaide mengeling van dimensies "dim 1"/"dim 2" noemen), maar er kwam niets voor in de plaats behalve twee vage lijntjes plus zwevende `axisTick`-streepjes op de nullijnen. Nu tekent de component een echt meegedraaid referentiekader: vloerraster in het dim1-dim3-vlak, ribben van de kubus, drie aslijnen vanuit de oorsprong en `dim n (x%)`-labels op de tippen — allemaal door dezelfde `projecteer()`, dus synchroon per constructie.

### Wat er verder in dezelfde ronde bij is gekomen

- **Perspectief in plaats van orthografisch.** `CAMERA_AFSTAND = 4` (in eenheden van `straal`); de isometrische look maakte de draairichting dubbelzinnig. Het venster houdt rekening met de maximale perspectiefvergroting, anders valt de voorste ribbe buiten beeld.
- **Luchtperspectief.** `mist()` mengt elke kleur naar de achtergrond naarmate een punt verder weg ligt — haalt in één bewerking verzadiging én contrast weg. Beeldsymbolen (logo's) kunnen geen kleur aannemen, die krijgen de mist via opacity.
- **Slepen zet geen filter meer om.** Het einde van een sleep was ook een `click`; nu geldt een marge van 4 px.
- **Zoom.** Scrollen in 3D zoomt (eigen `zoom`-ref), scrollen in 2D gebruikt ECharts' `dataZoom` type `inside` met `filterMode: "none"` — die laatste is belangrijk, want de standaard gooit punten uit de serie en dan springen de labels bij elke zoomstap. Knop "Aanzicht herstellen" reset beide.
- **Labels.** `labelLayout` staat op `{ hideOverlap: true, moveOverlap: "shiftY" }`, maar dat bleek een noodrem en geen ontwerp: welk label overleeft hangt af van de tekenvolgorde. Daarom houden alleen de 12 vaakst toegekende tags een vast label (`VASTE_TAGLABELS`), de rest komt bij hover. Rijen houden hun label, behalve als ze een logo hebben.
- **Partijlogo's als punt.** `lib/partyLogoSprite.ts` haalt de SVG op, leest de verhouding uit de `viewBox` (nodig, want ECharts perst een `image://`-symbool in het vak dat je opgeeft — zonder verhouding wordt PVV's 13:1 wordmerk een vierkant) en kan het logo herteken als contour in één inkt. CSS kan dat niet: het logo belandt op een canvas. Toggle "Logo's: in kleur / als contour", staat nu op contour. In personenweergave krijgt een spreker het logo van zijn partij.
- **Uitschieter-beleid.** `straal` is het **90e percentiel** van de puntafstanden, niet het maximum: één tag (`Ideologie-Links-Economisch`) ligt vier keer zo ver als de kern en perste met gelijk-aspect de rest tot een vlekje. In 2D viel dat niet op omdat elke as daar los schaalt. Gevolg: een handvol punten valt standaard buiten beeld, met een telling in de hint en een zoom-ondergrens (0,12) die ver genoeg uitzoomt om ze binnen te halen.
- **SGP-logo vervangen** door de 2016-versie van Wikimedia Commons (het oude bestand was verkeerd).

### Ontwerpsysteem voor de tagiconografie — geadopteerd, maar kijk er nog eens naar

`docs/design/tag-iconografie/` (verplaatst uit de repo-root, met een `docs/design/README.md` ernaast). `tag-styles.json` is het machineleesbare deel: per perspectief een kleur, marker en Lucide-icoon, en per tag een Lucide-icoon.

`frontend/scripts/build_tag_icons.mjs` genereert daaruit `src/lib/tagIcons.generated.ts`. Wat die stap doet: Lucide-iconen zijn een mix van `<path>`, `<circle>`, `<line>`, `<polyline>` en `<rect>`, en ECharts wil één padstring — dus alles wordt tot één `d` gesmolten, met twee lege `M`-sprongen ervoor die de bounding box op het volle 24×24-raster zetten (anders rekt ECharts elk icoon afzonderlijk uit tot het opgegeven vak). `lucide-static` is toegevoegd als **devDependency**; het gegenereerde bestand staat in de repo, dus Lucide belandt niet in de bundel.

**Zeven icoonnamen uit het ontwerpsysteem bestaan niet in Lucide** — `person-lectern`, `cheque`, `person-cap`, `resize-figure`, `round-table`, `voorzittershamer`, `paper`. Er staat nu een expliciete `VERVANGERS`-map in het generatiescript (bv. `voorzittershamer` → `gavel`, `cheque` → `hand-heart`). Die keuzes zijn van mij, niet van de ontwerper; laat ze nakijken.

**Openstaand punt, en het belangrijkste van deze sectie:** het geadopteerde palet is mono-accent — vier gedempte aardetinten (`#B68235`, `#4C7C7A`, `#B15E4A`, `#6B8558`). Het palet dat er stond was gevalideerd met de dataviz-validator tegen `--color-bg` in licht én donker met `--pairs all`; dit palet is dat niet, en het onderlinge kleurverschil is duidelijk kleiner. Het ontwerpsysteem vangt dat op met vorm ("perspectives are distinguished by tone + shape, not by clashing hues"), en de tagpunten dragen nu inderdaad hun eigen icoon. Maar: Lucide-iconen zijn lijntekeningen, dus de punten worden getekend met `itemStyle.borderColor` en een doorzichtige vulling — en op de screenshot van 2026-07-30 oogt de kaart daardoor **te licht en te vlak**, zeker in combinatie met de contourlogo's. Er is nog geen aparte donkere variant van het palet. Concreet nog te doen: contrast opnieuw meten, en overwegen de tagpunten wél te vullen (of de lijndikte op te voeren) zodat de wolk weer gewicht krijgt.

### Bestanden

Nieuw: `frontend/src/lib/partyLogoSprite.ts`, `frontend/src/lib/tagIcons.generated.ts`, `frontend/scripts/build_tag_icons.mjs`, `frontend/scripts/shoot_correspondence.mjs` (Playwright-hulpje: zet 3D aan, sleept, schiet screenshots naar `/tmp/correspondence-shots`), `docs/design/`.

Gewijzigd: `TagCorrespondenceMap.vue` (het leeuwendeel), `styles/main.css` (`.control-knop`, hogere grafiek in 3D), `package.json` (lucide-static), `public/party-logos/sgp.svg`.

**Let op:** er staan twee ongewenste bestanden in `frontend/public/party-logos/` — `logos.ai` en een `~ai-*.tmp`. Die horen daar niet; opruimen of in `.gitignore`.

### Nieuwe issue

**#7 — Taal in de codebase: vaste grens tussen Nederlands en Engels.** De repo mengt beide, soms binnen één functie (`correspondence.ts` heeft een Engelse API met Nederlandse helpers; `TagCorrespondenceMap.vue` Engelse props met Nederlandse locals). Voorstel in de issue: Engels voor alles wat met de techniek meepraat, Nederlands voor domeinbegrippen-als-waarde en voor commentaar/docs/commits, met een expliciete uitzondering voor domeinwoorden die niet vertaalbaar zijn.

## Stand bij einde sessie (2026-07-28)

Vervolg op de sessie van 2026-07-27 hieronder. Deze sessie ging over `agy` als tweede extractie-/taggingbackend naast de lokale qwen-pipeline — zowel een verworpen experiment (gebundelde prompts) als een geslaagde echte batch (single-call, zoals de bestaande aanpak).

- **Gebundelde (multi-document) extractieprompts getest en verworpen** — volledig uitgeschreven in nieuw `docs/batch-experiment.md`. Kort: 5 documenten per `agy`-call bespaart 66-80% prompt-tekens (geen scriptbare token-telling beschikbaar bij `agy`, dus tekens als proxy), en een automatische substring-check (elk `quote_text` moet letterlijk in de brontekst van het juiste document staan) vond geen grove cross-document citaat-verwisseling. **Maar** een inhoudelijke vergelijking tegen de bekende single-call-baseline (20 doc-ids, kalibratie van 2026-07-24) liet op 14 van de 20 documenten afwijkende resultaten zien, incl. een omgekeerde stance op doc 129 — en het is niet vastgesteld of dit door het bundelen zelf komt of door gewone modelvariatie (geen same-day controlemeting gedraaid). Besluit: single-document-per-call blijft de aanpak. Experiment-artefacten (`pipeline/prompts/extract_argument_batch.md`, `_build_batch_prompt()` in `pipeline/extract_arguments.py`, `scripts/agy_test_batch_extraction.py`) blijven in de repo als referentie, niet in productie gebruikt.
- **Nieuw `scripts/agy_run_extraction_batch.py`**: Stage 1-extractie via `agy` i.p.v. lokale qwen, zelfde contract als `pipeline/extract_arguments.py` (schrijft naar `arguments`/`claims`, zet `documents.extraction_attempted_at` + prompt/model-provenance). Draait single-doc-per-call. Analoog aan het bestaande `scripts/agy_run_tagging_batch.py`-patroon voor Stage 1b.
- **Twee echte batches gedraaid** (topic `stikstof`, model `gemini-3.6-flash-low`, dagquota ~100% → **14% resterend** aan einde sessie):
  - Extractie: 377 documenten, 2 fouten, 250 nieuwe arguments, 176 claims (`data/export/run-logs/agy_extraction_batch.log`). Empirisch tarief: **~0,10-0,11%/document**.
  - Tagging: alle 392 op dat moment ongetagde arguments (incl. de 250 nieuwe), 5 fouten, 784 derived tags, 2483 llm-tags (`data/export/run-logs/agy_tagging_batch_4.log`, vervolg op `agy_tagging_batch.log`/`_2.log`/`_3.log` (in data/export/run-logs/) van eerdere sessies). Empirisch tarief: **~0,10-0,15%/argument**.
  - **Belangrijk geleerd over quota-meting**: een eerdere same-day herhaling van dezelfde 20 documenten (het batch-experiment hierboven) gaf een quota-tarief dat een stuk gunstiger leek dan de kalibratie van 2026-07-24 — maar dat bleek vermoedelijk (deels) een cache-effect te zijn (letterlijk dezelfde documenttekst als 4 dagen eerder al eens naar Gemini gestuurd), niet een echt batching-voordeel. Bij het daadwerkelijke extractie-batch (verse, nooit eerder verwerkte documenten) kwam het tarief weer overeen met de oorspronkelijke kalibratie (~0,10%/doc). **Les: quota-vergelijkingen zijn alleen betrouwbaar op verse content**, hergebruikte testdocumenten geven een vertekend beeld.
  - Machine-power-gate (`feedback_llm_extraction_power_only`-memory) is bijgesteld: geldt alleen voor lokale LM Studio/qwen-inferentie op de M2 Max, **niet** voor `agy` (draait als losse API-call in Docker, geen zware lokale compute) — `agy`-batches mogen dus ook op accu draaien.
- **Stand na deze sessie**: `stikstof` staat op 2734/5213 documenten geprobeerd (2479 resterend), 1368 arguments totaal, slechts **5 ongetagd** (de foutgevallen uit de laatste batch). Dagquota `agy` op **14%** — waarschijnlijk niet genoeg voor nog een substantiële batch vandaag; volgende sessie moet zelf even `/usage` checken (nog steeds geen scriptbare check, zie sectie hieronder) voor een vers dagquotum.
- **Correctie op een eerdere aanname in deze sessie**: hieronder stond eerder dat de export niet opnieuw was gedraaid na de twee batches. Dat klopte niet — `make export TOPIC=stikstof` wás gedraaid (`status.json` was ~3 minuten stale t.o.v. de laatste taggingbatch, geen ongedraaide export). Alsnog opnieuw gedraaid ter controle; DB en export komen nu overeen (2734/5213 documenten, 1368 arguments, 1363 getagd, 5 ongetagd). **Les, in lijn met de waarschuwing verderop in dit document**: vertrouw bij twijfel de DB/`git diff`, niet blind de laatst geschreven sectie hier — ook niet binnen dezelfde sessie.
- **Nog niet gedaan**: de 5 taggingfouten uit de laatste batch zijn niet onderzocht/opnieuw geprobeerd. Alle wijzigingen van deze sessie én van 2026-07-27 (status-pagina, partij-klikfilter, minister-backfill, batch-experiment, agy-batches) zijn inmiddels wél gecommit (6 commits, main staat lokaal 12 commits voor op `origin/main`, nog niet gepusht).

## Stand bij einde sessie (2026-07-27) — verouderd, zie sectie hierboven

Vervolg op de sessie van 2026-07-26 hieronder (zelfde lopende gesprek, over de datumgrens heen). Alles hieronder staat nog **ongecommit** in de working tree (zie `git status`) — bewust, zodat er in één keer bekeken/gecommit kan worden.

- **Nieuwe `/status`-pagina**: publiek overzicht van pipeline-voortgang (documenten geëxtraheerd, arguments getagd, documenten redactie-gecheckt), per topic, met simpele voortgangsbalken. Databron: nieuwe `fetch_pipeline_status`/`status.json`-export in `pipeline/build_static_data.py` (draait automatisch mee met `build_static_data`, geen aparte stap). Frontend: `frontend/src/pages/status.astro` + CSS in `main.css` (`.status-*`-classes) + nav-link in `SiteNav.astro`. Bewust **geen** herhaling van de `/about`-pagina's "geen kwaliteitsoordeel/geen fact-checking"-framing op deze pagina — die hoort bij `/about`, andere pagina's blijven feitelijk/kort (zie ook memory `feedback_status_page_tone`).
- **Klik-op-partij-in-grafiek filtert argumenten** (was de aanleiding: "Onbekend"-balk in `StatsPanel.vue` deed niets bij klikken). Nieuw `frontend/src/lib/usePartyFilter.ts`, zelfde cross-island `CustomEvent`-patroon als het bestaande `useTagFilter.ts`. `StatsPanel.vue` zet de filter bij een klik op een bar-segment (nogmaals klikken = wissen, met dezelfde "alles tonen"-knop als de tag-filter). `ArgumentColumn.vue` combineert nu tag- én partij-filter (AND, beide onafhankelijk actief te zetten). "Onbekend" is een sentinel-partijnaam (zie hieronder), geen echte partijcode.
- **GitHub issue #2 (minister-partij) opgelost voor 3 van de 4 destijds onvindbare namen**, via twee nieuwe externe bronnen (geen AI, verifieerbaar) bovenop de al bestaande TK OData-route in `scripts/backfill_minister_info.py`:
  - **Jaimi van Essen → D66**: rijksoverheid.nl/regering/bewindspersonen/jaimi-van-essen. Let op: dit staat **niet** in de schema.org/JSON-LD op die pagina (die bevat alleen generieke WebPage/breadcrumb-metadata) maar als losse tekst ("Partij: D66") in de Next.js server-payload van de pagina — dus regex over de ruwe HTML, geen nette API.
  - **Jean Rummenie → BBB** en **Piet Adema → ChristenUnie**: via Wikidata (`P102`/lid-van-politieke-partij), opgevraagd via de publieke `Special:EntityData/<Q-id>.json`-API (niet de HTML-pagina scrapen — betrouwbaarder, machine-leesbaar). Rummenie zat niet meer op rijksoverheid.nl (uit functie), dus rijksoverheid was voor hem geen optie.
  - **Dick Schoof → `"Onafhankelijk"`** (i.p.v. NULL laten staan): Wikidata toont hem als PvdA-lid t/m 2021, en sindsdien (dus ook tijdens zijn premierschap) als onafhankelijk politicus. Bewuste waarde i.p.v. gok — hij hoort niet bij "Onbekend" (data-hiaat) maar ook niet bij een bestaande fractie. Dit is nu ook de reden dat "Onbekend" in de UI een echte restcategorie is geworden (alleen nog data-hiaten, geen "eigenlijk wel bekend maar nooit opgezocht"-gevallen meer).
  - **Onderzocht maar niet bruikbaar gebleken**: Nationaal Archief-dataset `nt00334` (rijk gestructureerde CSV's: `FUNCTIE`/`KABINET`/`PERSOON`, met een eigen `partij`-kolom) — goede kwaliteit maar dekt alleen tot en met het vierde kabinet-Balkenende (~2007-2010), te oud voor het huidige kabinet.
  - `MINISTER_PARTY`-dict in `backfill_minister_info.py` uitgebreid met deze 4 namen, dry-run + echte run gedraaid, gevolgd door een verse `build_static_data`-export. **Alleen Piet Adema had al arguments met NULL party in de stikstof-dataset vóór deze sessie zichtbaar** (samen met Van Essen/Rummenie/Schoof) — na deze backfill staat "Onbekend" op 0 voor stikstof (Adema had toevallig geen stikstof-arguments, dus geen zichtbaar effect voor hem specifiek, maar de dict is nu wel compleet voor een volgend topic).
- **Stage-1-batch twee keer hervat en weer gestopt binnen deze sessie** (stroom → accu → stroom → accu, netjes elke keer via `kill` + `lms unload --all`, geen corrupte state dankzij per-document commit). **Stand bij laatst stoppen: 2407/5213 documenten geprobeerd, model unloaded.** Zelfde hervat-commando als altijd (zie sectie "Setup om verder te werken" verderop).
- **Nog niet gedaan**: de wijzigingen van deze sessie (status-pagina, partij-klikfilter, minister-backfill) zijn nog niet gecommit, en de frontend is niet visueel in een browser getest na de partij-klikfilter-wijziging (wel geverifieerd dat de pagina zonder fouten rendert via curl/dev-server-logs). Bij twijfel: `/topics/stikstof/` openen, op de "Onafhankelijk"- of een andere partij-balk klikken, controleren dat de kolommen filteren.

## Stand bij begin sessie (2026-07-26) — verouderd, zie sectie hierboven

Bij het begin van deze sessie bleek de sectie hieronder ("Stand bij einde sessie 2026-07-25") **achterhaald**: een latere sessie diezelfde avond had al substantieel werk gedaan (bestandstijden 22:00–22:01, laatste DB-write 00:46) dat toen niet meer in dit document is bijgewerkt en ook nog ongecommit stond. Voor het vervolg dus: vertrouw bij twijfel de DB/`git status`/`git diff`, niet blind de laatst geschreven sectie hieronder.

- **Crawler uitgebreid naar Commissiedebatten** (`crawlers/tweede_kamer/tweede_kamer/odata.py`, `spiders/verslagen.py`): eerder ondersteunde `vergadering_url_for_activiteit`/`pick_closest_vergadering` alleen `Vergadering.Soort='Plenair'`. Nu ook `'Commissie'`, met een titel/onderwerp-woordoverlap-tiebreaker (`_title_words`/stopwoordenlijst) — nodig omdat op drukke commissiedagen tientallen commissies parallel lopen en datum-nabijheid alleen dan niet volstaat. Twee empirisch gevonden misser-gevallen (2025-06-18: 10 same-day kandidaten, verkeerde gekozen zonder titel-tiebreak; een "OMGEZET in schriftelijk overleg"-Activiteit die matchte met een compleet ongerelateerd commissiedebat) staan als comment in `odata.py`. Zonder woordoverlap geeft `pick_closest_vergadering` bewust `None` terug (gemiste match) in plaats van te gokken. Resultaat: het stikstof-corpus groeide van 3949 → **5213 documenten**.
- **`documents.is_voorzitter_turn`-kolom toegevoegd** (schema.sql + `pipeline/ingest/ingest_tk.py`) — lost de al langer bekende kwestie op dat de voorzitter (bv. Paulusma/D66, Krul/CDA) als gewone actor met partij-attributie werd opgeslagen wanneer die procedureel het woord voerde. Gedetecteerd via `build_parent_map`/`is_voorzitter_turn`: de dichtstbijzijnde omsluitende `<activiteitdeel><titel>` bevat "voorzitter" (bv. "Spreekbeurt - De voorzitter") — `<spreker><functie>` zelf draagt geen rolmarkering, blijft altijd "lid Tweede Kamer". Fractie in de brondata blijft ongewijzigd, dit is puur een rol-vlag.
- **`scripts/backfill_voorzitter_turns.py`** (nieuw): eenmalige backfill over de bestaande 3949 documenten (die al vóór deze kolom bestonden) + `--purge-arguments` om arguments die al ten onrechte uit voorzitter-beurten geëxtraheerd waren alsnog te verwijderen (incl. afhankelijke claims/argument_tags/argument_oppositions). **Geverifieerd**: 156 documenten geflagd als voorzitter-beurt, 0 documenten met `is_voorzitter_turn=1` hebben nu nog arguments in de DB — de purge is schoon doorgevoerd.
- `pipeline/extract_arguments.py` (`fetch_pending_documents`) en `scripts/pipeline_status.py` filteren/rapporteren nu op `is_voorzitter_turn = 0`.
- **Stage-1-batch was al verder gevorderd dan hierboven gemeld**: laatste `extraction_attempted_at` stond op 2026-07-25T22:46:58Z (document-id 2236), dus de batch is na de "1199/3949"-stand hieronder gewoon doorgelopen (waarschijnlijk in dezelfde late sessie die de crawler/voorzitter-wijzigingen deed) — maar dat verliep buiten `data/export/run-logs/extract_batch_full.log` (dat logbestand is stil sinds 10:01 die ochtend), dus de details van die run zijn alleen uit de DB af te leiden, niet uit logs. Bij hervatten (nu weer op stroom): **2951 documenten pending** (van de 5213, exclusief 156 voorzitter-beurten).
- Deze wijzigingen (crawler, schema, ingest, extract_arguments, pipeline_status, backfill-script) stonden aan het begin van deze sessie nog **ongecommit** in de working tree, samen met een losstaande, al-gestagede frontend-redesign (fonts, `useTheme.ts`, CSS, nav/stats/tags-componenten). Beide zijn in deze sessie als aparte commits vastgelegd (zie git-log voor de exacte commit-hashes).
- `data/bipolariteit.db.bak-20260725220207` was een ongetrackt lokaal backup-bestand van vóór de purge-stap — bewust niet in git, blijft lokaal liggen.

## Stand bij einde sessie (2026-07-26)

- Stage-1-batch hervat op stroom (`lms load qwen/qwen3.6-27b` + `extract_arguments.py --topic stikstof --limit 4000`), daarna bewust gestopt (`kill`, geen crash) omdat de gebruiker moest gaan unpluggen. Model expliciet unloaded (`lms unload --all`).
- **Stand bij stoppen: 2287/5213 documenten geprobeerd (max doc-id 2341), 1034 arguments.** Nog ~2870 documenten te gaan (van de 5213, exclusief 156 voorzitter-beurten).
- Hervatten zodra weer op stroom: zelfde commando als hierboven in de sectie "Stand bij begin sessie (2026-07-26)", pakt automatisch verder via het skip-mechanisme.
- Verse export gedraaid (`make export TOPIC=stikstof`) tegen de 1034-argument-stand — `data/export/topics/stikstof.json`/`topics-index.json` zijn nog **niet gecommit** (bewust, want de batch loopt nog door en deze export is dus alweer een tussenstand; opnieuw draaien vóór commit als er een "definitieve" snapshot nodig is).

### Extra `agy`-tagging-batch: bijgewerkte quota-kalibratie (derde meting)

Nog wat reservequota bij `agy` beschikbaar (gebruiker gaf ~20% budget vrij, `We're at 100%`) — ingezet als extra validatie-/doorvoerbatch bovenop de bestaande lokale tagging (niet i.p.v.), zelfde afweging als eerder (zie sectie "`agy` als tagging-validatiemiddel" hierboven): batch-tagging via `agy` blijft te duur voor de vólle batch, maar is bruikbaar voor gerichte extra doorvoer binnen een quota-budget.

```bash
open -a Docker   # als de daemon nog niet draaide
PYTHONPATH=. uv run python scripts/agy_run_tagging_batch.py --topic stikstof --limit 130
```

**Resultaat: 130 argumenten getagd, 0 fouten, 260 derived + 804 llm tags, gem. 6.3s/argument** (id 40 t/m 169). Tagged-totaal nu **168** (was 38). Quota 100% → 84.47% = **15.53% voor 130 argumenten, ~0.12%/argument** — iets gunstiger dan de eerdere meting (~0.154%/argument bij een kleinere taxonomie), dus binnen het opgegeven 20%-budget; geen noodstop nodig geweest ondanks dat een tussentijdse meting (92%→89% over documenten 40-78) op een schijnbaar hoger tempo (~0.205%/doc) wees — die tussenmeting bleek achteraf ruis, niet de trend. **Les voor een volgende keer**: één tussentijdse `/usage`-meting vroeg in een batch is te ruisgevoelig om een noodstop op te baseren; minstens twee metingen verspreid over de batch (zoals nu toevallig gebeurde) geven een betrouwbaarder beeld.

### Frontend: correspondentie-export, een echte compilerbug, en minister-weergave

Ná de agy-batch verder gewerkt aan de website (nog steeds 2026-07-26). Alle wijzigingen hieronder zijn gecommit (zie `git log`: `7d143ec`, `6e0b638`, `0db997c`).

- **Verse export + correspondentieanalyse**: `make export TOPIC=stikstof` gedraaid tegen de 1034-argument-stand. `build_correspondence_analysis` (in `build_static_data.py`) draait al automatisch mee in de export, geen aparte stap nodig.
- **Echte bug gevonden en gefixt: kolomkoppen toonden altijd hetzelfde (verkeerde) aantal.** `ArgumentColumn.vue` had een prop letterlijk genaamd `arguments`. Dat botst met het ingebouwde JS `arguments`-object dat elke niet-arrow functie heeft — Vue's templatecompiler laat zulke botsende globale namen (whitelist met o.a. `Math`, `Date`, `arguments`) in de template *ongemoeid* i.p.v. ze naar de prop te resolven. Dus `{{ arguments.length }}` in de template gaf stilzwijgend de lengte van dat native object terug (steevast hetzelfde getal, ongeacht de echte data) — vandaar dat Pro/Contra/Onduidelijk allemaal exact hetzelfde (onzinnige) aantal toonden. **Fix**: prop hernoemd naar `argumentList` (`ArgumentColumn.vue` + `[slug].astro`). Na de fix kloppen de aantallen weer (Pro 399, Contra 628, Onduidelijk 7). **Les voor de toekomst**: noem nooit een prop/variabele `arguments` in Vue-templates (of `eval`, `arguments`, en de andere entries in Vue's compiler-whitelist) — de fout is stil, geen crash, geen warning.
- **Bewindspersonen tonen nu een rol i.p.v. niets.** 9 actors hadden `party = NULL` omdat ze als Minister/Staatssecretaris spreken (VLOS `<spreker soort="Minister">` heeft geen `<fractie>`). Nieuwe kolom `documents.speaker_role_title` (schema.sql + `ingest_tk.py`) vangt de VLOS `<functie>`-tekst (bv. "minister van Landbouw, Visserij, Voedselzekerheid en Natuur") voor niet-Kamerlid-sprekers op, getoond op elke `ArgumentCard` ongeacht of de partij bekend is. **`scripts/backfill_minister_info.py`** (nieuw) vult dit met terugwerkende kracht (873 documenten) en backfilt daarnaast **de echte partij** voor 5 van de 9 actors via de TK OData Persoon/FractieZetelPersoon-API (geen AI, een verifieerbare bron): Wiersma→BBB, Erkens/Van der Wal(-Zeggelink)/Harbers→VVD.
  - **Voor Dick Schoof, Jean Rummenie, Piet Adema, Jaimi van Essen is géén partij vindbaar** — bevestigd via twee onafhankelijke OData-paden (`Persoon?$filter=contains(Achternaam,...)` geeft niets terug; `ActiviteitActor?$filter=contains(ActorNaam,...)` vindt wél een `Persoon_Id` voor Schoof, maar dat `Persoon`-record is volledig leeg/een stub, en heeft geen `FractieZetelPersoon`-geschiedenis). Voor Schoof klopt dit ook met de werkelijkheid (partijloos premier). **party blijft bewust NULL voor deze 4** — geen gok, een geverifieerde afwezigheid. Gedocumenteerd als **GitHub issue [#2](https://github.com/SiggyF/bipolariteit/issues/2)** voor wie dit verder wil uitzoeken (bv. `PersoonLoopbaan`/`PersoonNevenfunctie` nog niet geprobeerd).
- **Correspondentiekaart: compactere tooltip + klik-om-te-filteren.** Tooltip van de tag-scatter had geen breedtelimiet (lange `beschrijving`-teksten liepen over het scherm) — nu `max-width: 220px` + word-wrap. Klikken op een tag-punt filtert de Pro/Contra/Onduidelijk-kolommen naar alleen argumenten met die tag (nogmaals klikken = wissen). Cross-island state (elke Astro/Vue-eiland is een aparte Vue-app-instantie, een gewone module-scope `ref` wordt dus niet gedeeld) via een DOM `CustomEvent`, zelfde patroon als `useTheme.ts` al gebruikte voor de dark-mode-toggle — nieuw bestand `lib/useTagFilter.ts`.
- Dev-server tijdens dit werk een aantal keer herstart (`astro dev stop` + `astro dev --background`) om zeker te zijn van verse data/code, niet omdat Vite/Astro caching zelf het probleem was (zie de "echte bug" hierboven).

### Nog openstaand voor een volgende sessie
- Stage-1-batch verder afmaken (zie "Stand bij stoppen" hierboven, ~2870 documenten te gaan) en daarna Stage 2 volle batch.
- GitHub issue #2 (minister-partij) — geen actie vereist, puur gedocumenteerd voor later.
- `activiteit_soort` staat nog op NULL voor alle documenten (zie eerdere sessie) — nog niet opgepakt.
- Correspondentiekaart-klikfilter is geïmplementeerd maar **niet visueel getest in een browser** deze sessie (gebruiker had de Claude-in-Chrome-extensie niet geïnstalleerd) — wel geverifieerd dat de databinding (`argument.tags[].sleutel` ↔ filterlogica) klopt en de pagina zonder fouten rendert. Bij twijfel: handmatig een tag aanklikken op `/topics/stikstof/` en controleren dat de kolommen filteren.

## Stand bij einde sessie (2026-07-25) — verouderd, zie sectie hierboven

## Stand bij einde sessie (2026-07-25) — begin hier bij een nieuwe sessie

- **Stage-1-batch opnieuw op accu gepauzeerd, bewust gestopt (geen crash).** Bij het begin van deze sessie bleek het proces van de vorige sessie (PID 22133/22135) niet meer te leven (machine was kennelijk in slaap/herstart geweest zonder dat het proces netjes afsloot) en LM Studio had geen model meer geladen. Model opnieuw geladen (`lms load qwen/qwen3.6-27b`) en de batch herstart met exact hetzelfde commando; pakte automatisch verder via het skip-mechanisme bij document 977. Na ~1,5 uur (977→1199/3949 documenten geprobeerd, 520→610 arguments) gebruiker naar accu, proces netjes gekild (`kill`, per-document commit dus geen corrupte state) en het model in LM Studio expliciet unloaded.
- **Status bij einde sessie: 1199/3949 documenten geprobeerd, 610 arguments.** Onderweg 11 transiente fouten gezien (mix van `Read timed out` na 120s en `400 Bad Request`) — zelfde bekende patroon als eerdere sessies, die documenten blijven pending en worden automatisch opnieuw geprobeerd bij een volgende run; geen actie nodig.
- **Model is nu unloaded** (`lms unload --all` gedraaid) — bij hervatten dus eerst opnieuw `lms load qwen/qwen3.6-27b` vóór de batch te herstarten.
- **Check voortgang bij hervatten**: `tail -f data/export/run-logs/extract_batch_full.log`, of `uv run python -c "from pipeline.db import db; c=db.connect(db.DEFAULT_DB_PATH); print(c.execute('SELECT COUNT(*) FROM documents WHERE extraction_attempted_at IS NOT NULL').fetchone()[0])"`. Nog ~2750 documenten te gaan, geschat ~9-10 uur bij het eerder gemeten gemiddelde.
- Na afloop: `build_static_data.py` opnieuw draaien voor een verse export, en dan Stage 2 (`redactie_check.py`) op de volle batch overwegen (zelfde LM Studio-instance, dus wachten tot Stage 1 klaar is).
- **Hervatten zodra weer op stroom**: model laden, dan exact hetzelfde commando starten, pakt automatisch verder dankzij het skip-mechanisme (`extraction_attempted_at`, per-document commit):
  ```bash
  export PATH="$HOME/.lmstudio/bin:$PATH"
  lms load qwen/qwen3.6-27b
  nohup uv run python -m pipeline.extract_arguments --topic stikstof --limit 4000 >> data/export/run-logs/extract_batch_full.log 2>&1 &
  ```
- **Stage 2 (`redactie_check.py`) is deze sessie gebouwd en werkt**, maar de volle Stage-2-batch is nog niet gestart (zie sectie verderop) — bewust, om niet te concurreren met Stage 1 op dezelfde LM Studio-instance. Volgorde bij hervatten: eerst Stage 1 afmaken, dán pas een volle Stage-2-batch overwegen (of ze om en om in kleine porties laten lopen als dat sneller moet).
- Direct daarna nuttig, geen LLM nodig: `uv run python -m pipeline.build_static_data --topic stikstof` (verse export) — maar overweeg eerst of oppositions/redactie-data al meegenomen moet worden (nog niet geïmplementeerd, zie Stage 2-sectie).

## Setup om verder te werken

```bash
cd /Users/baart_f/src/bipolariteit
uv sync            # installeert dependencies (requests, pytest) in .venv
uv run pytest tests/ -v
```

Python-dependencies worden beheerd met `uv` (niet pip/venv handmatig, ook niet voor losse scratch-scriptjes: altijd `uv run python ...`). Nieuwe dependency toevoegen: `uv add <pkg>` (of `uv add --dev <pkg>` voor test-only).

`pyproject.toml` heeft nu `[tool.pytest.ini_options] pythonpath = ["."]` — nodig omdat `tests/` geen `__init__.py` heeft, waardoor pytest zonder deze regel de repo-root niet op `sys.path` zet en `import pipeline...` in testbestanden faalt.

## Voortgang (taken uit het plan)

1. ✅ Repo-scaffold + `.gitignore` (data/raw en *.db uitgesloten)
2. ✅ `pipeline/db/schema.sql` + `tests/test_schema_neutrality.py` (slaagt) — 8 tabellen aangemaakt en geverifieerd via `pipeline/db/db.py`
3. ✅ `crawlers/tweede_kamer/` — herschreven als Scrapy-project (`scrapy.cfg` + `tweede_kamer/` package: `settings.py`, `items.py`, `pipelines.py`, `odata.py`, `paths.py`, `spiders/verslagen.py`), consistent met het `scrapy_news/`-plan. Alle empirisch gevonden logica (datumheuristiek, `best_verslag`-voorkeur, `limit*3`-oversampling, dedup) 1-op-1 overgenomen uit de oude `tk_client.py`/`fetch_tk.py`. Geverifieerd: `uv run scrapy crawl verslagen -a topic=stikstof -a limit=5` (uitvoeren vanuit `crawlers/tweede_kamer/`) vindt exact dezelfde 5 verslag-IDs in dezelfde volgorde als de oude client, JSON-metadata byte-identiek. Oude `tk_client.py`/`fetch_tk.py` verwijderd (geen hybride).
   - Let op: Scrapy 2.17 heeft `start_requests()` volledig verwijderd uit de basisklasse (geen backwards-compat shim); de spider gebruikt `async def start(self)` in plaats daarvan.
4. ✅ `pipeline/ingest/ingest_tk.py` — segmenteert VLOS-XML per sprekerbeurt (woordvoerder + interrumpant, generiek gedetecteerd) naar `documents`/`actors`-rijen. Getest: `uv run pytest tests/test_ingest_tk.py` (naam-reconstructie + topic-filter + turn-detectie) en handmatig geverifieerd tegen alle 5 verslagen (3949 documenten, 50 actors).
   - **Naambug gevonden en gefixt**: de TK-bron plakt Nederlandse tussenvoegsels soms achteraan `achternaam` voor sorteerdoeleinden (bv. `achternaam="Plas van der"` i.p.v. "Van der Plas"), en soms een Arabisch "El"-voorvoegsel ook achteraan (bv. "Boujdaini El"). `_speaker_name`/`_reorder_achternaam` reconstrueert nu de juiste volgorde (incl. kleine letter bij tussenvoegsel na een voornaam: "Caroline van der Plas", maar "Van der Plas" zonder voornaam). Dit was cruciaal om nu te fixen, niet later: elk argument in latere stages erft de actor-naam, dus een verkeerde naam had zich overal doorheen verspreid.
   - **Bewuste, nog niet opgeloste kwestie**: de voorzitter (bv. Paulusma/D66, Krul/CDA) wordt als gewone actor met partij opgeslagen wanneer die procedureel het woord voert (bv. "Ik stel voor dat..."). Dit is procedurele tekst, geen politiek argument — maar wordt nu wél als `documents`-rij met partij-attributie bewaard. Dit is *bewust* doorgeschoven naar Stage 1 (LLM-extractie moet dit soort niet-argumentatieve voorzitter-chatter simpelweg geen argumenten opleveren), niet stilzwijgend genegeerd. Als dat niet vanzelf gebeurt, moet `extract_arguments.py` of `ingest_tk.py` alsnog voorzitter-turns filteren/markeren.
5. 🔶 Stage 1 LLM-extractie (`pipeline/extract_arguments.py` + `pipeline/prompts/extract_argument.md`) — werkt, promptversionering toegevoegd, volle batch onderweg maar **gepauzeerd op batterij bij 896/3949 documenten** (zie "Stand bij einde sessie" bovenaan). Zie sectie hieronder voor de kwaliteitsvergelijking tussen modellen.
6. ✅ Tag-taxonomie geïntegreerd (`data/tags.toml` → `pipeline/db/seed_tags.py` + `pipeline/tag_arguments.py`) — zie sectie hieronder. Lokale batch nog niet volledig doorgelopen (39/234+ getagd bij laatste meting), wacht op meer Stage-1-output.
7. ✅ Stage 2 redactie-check (`pipeline/redactie_check.py` + `prompts/redactie_bias_check.md`) — gebouwd en gevalideerd deze sessie, zie eigen sectie hieronder. Volle batch nog niet gedraaid (wacht op Stage 1).
8. 🔶 `build_static_data.py` JSON-export — bestaat en werkt (stats, tags-per-partij, correspondentieanalyse), exporteert nu ook Stage-2-data: `document.redactie_review` (pass_status/notes per document) en `oppositions` (symmetrische lijst tegenargumenten per argument, via nieuwe `fetch_redactie_reviews`/`fetch_oppositions`). Geverifieerd op de live DB: 478 argumenten geëxporteerd, 18 met oppositions, 11 met een redactie_review. **Nog niet gedaan**: dit visueel tonen in de frontend (ArgumentCard.vue kent deze velden nog niet) — puur de export-kant is deze sessie afgerond.
9. ✅ Astro+Vue frontend-scaffold — werkende v1 (`frontend/`), zie eigen sectie hieronder. Toont nog geen opposition-links (afhankelijk van punt 8).
10. ⬜ `run_walking_skeleton.sh` + volledige verificatie

## Belangrijke ontdekkingen tijdens de spike (Tweede Kamer OData API)

Deze zaten niet in de officiële documentatie en moesten empirisch getest worden — belangrijk om te weten voor wie hieraan verder bouwt:

1. **Geen directe FK tussen Activiteit en Vergadering.** De API documenteert geen `Vergadering_Id` op `Activiteit`. `tk_client.find_vergadering_for_activiteit()` gebruikt een datum-heuristiek (±1 dag, `Kamer='Tweede Kamer'`, `Soort='Plenair'`) om de juiste Vergadering te vinden, en kiest bij meerdere kandidaten de dichtstbijzijnde datum. Getest en werkend voor 10/10 stikstofdebatten sinds 2019.
2. **Tijdzone-valkuil**: `Vergadering.Datum` staat opgeslagen als lokale middernacht met `+01:00`/`+02:00`-offset. Een OData `$filter` met een `Z` (UTC) datumgrens op exact dezelfde kalenderdag mist die rij, omdat lokale middernacht in UTC vóór middernacht valt. Oplossing: query met een dag marge (−1/+1) in plaats van een exacte daggrens.
3. **VLOS XML-structuur** van een Verslag-resource (`GET /Verslag/{id}/resource`): namespace `http://www.tweedekamer.nl/ggm/vergaderverslag/v1.0`. Relevante nesting:
   `<vergadering><activiteit onderwerp="...">...<activiteitdeel soort="Spreekbeurt">...<activiteititem soort="Woordvoerder"><woordvoerder><spreker fractie=... weergavenaam=.../><tekst><alinea><alineaitem>...</alineaitem></alinea></tekst></woordvoerder>`.
   Segmentatie voor `ingest_tk.py`: filter top-level `<activiteit>` op `onderwerp` bevat het topic-keyword, zoek daarbinnen alle `<woordvoerder>`-elementen (spreker + tekst = één document/sprekerbeurt). Zie `/tmp/sample_verslag.xml` voor een volledig voorbeeld (niet gecommit, lokaal scratch-bestand — na een reboot moet dit opnieuw gedownload worden via `fetch_tk.py`).
4. **`tkapi`-package overwogen** (PyPI, Python ORM voor deze API): biedt geen ondersteuning voor de twee lastige stukken die wij nodig hebben (resource-XML downloaden, Activiteit↔Vergadering-koppeling), dus bewust niet toegevoegd als dependency — onze eigen `tk_client.py` doet dit al en is getest.
5. **Bronlink nog niet definitief**: `fetch_tk.py` slaat momenteel de OData resource-URL op als `source_resource_url` (verifieerbaar, technisch correct) maar NIET een publieke `tweedekamer.nl`-debatpagina-URL — dat patroon is nog niet uitgezocht en mag niet gegokt worden. Dit moet nog opgelost worden vóór `build_static_data.py` de `documents.url`-kolom vult (zie plan: elk argument moet een link naar de brontekst hebben).

## Stage 1 LLM-extractie: script staat er, klaar voor kwaliteitsvergelijking + volle run

`pipeline/extract_arguments.py` (CLI, gebruikt `pipeline/prompts/extract_argument.md`) leest per document (sprekerbeurt) de tekst, stuurt 'm naar een lokaal LLM via LM Studio's OpenAI-compatibele API, en schrijft `arguments`+`claims`-rijen weg. Gebruik:

```bash
uv run python -m pipeline.extract_arguments --topic stikstof --limit 15 [--min-id N] [--model ...] [--dry-run]
```

- `--dry-run`: extraheert en print, schrijft niets weg (gebruikt voor alle tests tot nu toe).
- `--min-id`: sla documenten met een lager id over — handig omdat de eerste ~40 documenten van het stikstofdebat grotendeels procedureel zijn (opening, welkomstwoord); pas vanaf document-id ~40 begint echte inhoudelijke wisseling (Van der Plas/Bromet/Heutink-discussie).
- Idempotent voor documenten die al minstens 1 argument opleverden (die worden overgeslagen bij een herhaalde run) — **maar niet voor documenten die 0 argumenten opleverden** (bv. procedurele tekst): die hebben geen rij om aan te herkennen en worden bij elke run opnieuw verstuurd. Voor de steekproeffase is dat geen probleem; vóór de volle batch-run moet dit nog een eigen skip-mechanisme krijgen (bv. een `processed_documents`-log of -tabel), anders wordt bij een onderbroken/herstarte volle run onnodig dubbel werk gedaan.
- Prompt verbiedt expliciet een waardeoordeel; voorzitter-/procedurele tekst levert per instructie 0 argumenten op (**punt 4 uit de eerdere sectie hierboven is hiermee opgelost**: getest en bevestigd — documenten 43, 44, 46-49, 52-54 (allemaal voorzitter/orde-tekst) leverden terecht 0 argumenten op in de laatste testrun).

**Testresultaat (`--topic stikstof --limit 15 --min-id 40 --dry-run`, model `qwen/qwen3.6-27b`, `reasoning_effort=none`):** 15 documenten, 0 fouten, 11 argumenten + 10 claims geëxtraheerd, kwalitatief correct (procedurele turns terecht overgeslagen, inhoudelijke turns van Van der Plas/Bromet/Heutink correct als pro/contra-argumenten met claims herkend). Latency: gem. 13.0s/doc (min 3.3s, max 43.9s — hangt sterk af van turnlengte). **Op dat gemiddelde: ~14.3 uur voor de volle 3949 documenten.** Dat is technisch haalbaar (overnight run) maar nog niet als zodanig gedraaid of geverifieerd op een langere steekproef.

### Nog open, volgende concrete stappen
1. ✅ **Kwaliteitsvergelijking tussen modellen gedaan.** Nieuw script `scripts/compare_models.py` (los van `extract_arguments.py` — negeert bewust de `extraction_attempted_at`-skipfilter zodat je hetzelfde vaste documentbereik `id 40-54` steeds opnieuw kan doorrekenen ongeacht wat er al écht verwerkt is; schrijft niets naar de DB, puur console-output). Gebruik: `PYTHONPATH=. uv run python scripts/compare_models.py <model>` (let op: móet vanuit de repo-root met `PYTHONPATH=.`, anders vindt Python de `pipeline`-package niet omdat het script-pad vóór de cwd in `sys.path` staat).

   Resultaat, alle drie op exact dezelfde 15 documenten (id 40-54, topic stikstof):

   | model | gem. latency | geschat volle batch (3949 docs) | argumenten | claims | belangrijkste probleem |
   |---|---|---|---|---|---|
   | `qwen/qwen3.6-27b` | 13.0s | ~14.3u | 11 | 10 | geen gevonden — correcte procedurele filtering, correcte stance/typology |
   | `google/gemma-4-e4b` | 3.3s | ~3.6u | 23 | 2 | over-extractie (knipt één punt op in meerdere "argumenten"), extraheert kale vragen als argument, veel `stance=unclear`/`typology=other` als vluchtheuvel, claims bijna afwezig |
   | `google/gemma-4-31b` | 10.8s | ~11.8u | 8 | 1 | mist een echte inhoudelijke beurt volledig (doc 51 — qwen vond daar 4 argumenten, gemma-31b 0), dezelfde "vergunningverlening"-quote die qwen correct `contra/economic` tagt wordt hier `unclear/other`, claims-extractie vrijwel afwezig |

   **Besluit: `qwen/qwen3.6-27b` blijft de keuze.** Beide gemma-modellen zijn sneller maar leveren merkbaar mindere kwaliteit in — gemma-e4b is te onnauwkeurig om bruikbaar te zijn, gemma-31b is maar ~17% sneller terwijl het echte argumenten en bijna alle claims mist. De ~14 uur voor de volle 3949 documenten (overnight run) is de juiste afweging.
2. Doorvoertijd (~14 uur) is nu bevestigd op basis van 15 documenten, waarvan de meeste inhoudelijk — dus nog steeds een overschatting van het gemiddelde over de hele dataset (die ook veel korte procedurele turns bevat, zoals 43/44/46-49/52-54 hierboven). Een langere steekproef (~50-100 docs) zou een stabieler gemiddelde geven, maar is niet blokkerend voor de volle run.
3. ✅ **Skip-mechanisme voor 0-argument-documenten gebouwd.** Nieuwe kolom `documents.extraction_attempted_at` (schema.sql + handmatige `ALTER TABLE` op de live DB, zelfde eenmalige aanpak als eerder bij `arguments.tagged_at`), gezet ná elke LLM-call (ook bij 0 resultaat), niet alleen bij een geslaagde extractie. `fetch_pending_documents` filtert nu op `extraction_attempted_at IS NULL` i.p.v. `NOT IN (SELECT document_id FROM arguments)`. Bestaande 12 documenten met al bekende arguments zijn met terugwerkende kracht gemarkeerd (`extracted_at` van hun eerste argument). Geverifieerd: 3 procedurele 0-argument-documenten (43, 44, 46) tweemaal achter elkaar gedraaid — tweede run sloeg ze terecht over en ging door naar 47-49, i.p.v. ze opnieuw te versturen. `uv run pytest tests/` blijft groen (16 tests, dit pad had nog geen eigen tests).
4. Nu modelkeuze en skip-mechanisme beide klaar zijn: de volledige batch draaien (`uv run python -m pipeline.extract_arguments --topic stikstof --limit 4000`, overnight), en daarna verder met Stage 2 (`redactie_check.py`).

### ✅ Recall-probleem metadiscours-argumenten gefixt

`qwen/qwen3.6-27b` gaf eerder `{"arguments": []}` terug op een Heutink-beurt (document-id 150) die inhoudelijk overduidelijk over de *legitimiteit van het debat zelf* ging ("Dit is geen dunne lijn", "Ik ga geen grens over" — verzet tegen een mogelijke inperking door de voorzitter). Dat was geen terecht 0-argument/procedureel geval, maar een gemist argument — een recall-probleem, iets anders dan het `extraction_attempted_at`-skipmechanisme (dat voorkomt alleen dat al-verwerkte documenten dubbel verstuurd worden).

**Fix toegepast** in `pipeline/prompts/extract_argument.md`: nieuwe regel die expliciet onderscheid maakt tussen procedurele voorzitters-chatter (geen argument) en metadiscours — uitingen over legitimiteit/reikwijdte/bevoegdheid/spelregels van het debat zelf (wél een argument, met `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting duidelijk is).

**Geverifieerd**:
- Document 150 (de bekende Heutink-metadiscours-beurt) levert nu correct 1 argument op (`stance: unclear`, `typology: other`, quote_context correct herkent de zelfreferentiële aard van de uiting).
- Regressietest op de vaste steekproef id 40-54 (via `scripts/compare_models.py qwen/qwen3.6-27b`) blijft consistent: 14 argumenten/14 claims, procedurele documenten (43, 44, 47, 49, 52-54) leveren nog steeds terecht 0 argumenten op. Geen regressie.
- Nog niet opnieuw tegen de volle 200-doc steekproefbatch getest (die batch was met de oude prompt gedraaid, zie hieronder) — dat gebeurt impliciet zodra de review-doc-stap (volgende sectie) opnieuw gegenereerd wordt met de gefixte prompt op vers geëxtraheerde documenten, maar de al-geschreven 137 arguments in de DB zijn met de oude prompt geëxtraheerd en dus niet met terugwerkende kracht gecorrigeerd.

### Grotere steekproefbatch gestart (achtergrondproces, status bij einde sessie: nog lopend)

Om een ~50 pagina's review-document te bouwen voor externe (Gemini-)validatie van de Stage-1-extractiekwaliteit is een bredere batch gedraaid:
```bash
uv run python -m pipeline.extract_arguments --topic stikstof --limit 200
```
✅ **Compleet** (afgerond ná het schrijven van de vorige versie van deze sectie): 200 documenten verwerkt, 0 fouten, 118 nieuwe arguments + 98 claims deze batch. Totaal nu **137 arguments** in de DB (was 19 bij start van de sessie). Latency gem=12.5s/doc, geschat volle batch (3949 docs) ≈ 13.7 uur — consistent met eerdere schatting.

**Voortgang:**
1. ✅ Extractieprompt gefixt voor het metadiscours-recallprobleem hierboven (`pipeline/prompts/extract_argument.md`), + hertest (zie sectie hierboven).
2. ✅ `scripts/build_extraction_review_doc.py` gedraaid → `data/export/extractie_review_stikstof.md` (137 argumenten, 9112 woorden, ~18 pagina's).
3. ✅ Antwoord van Gemini verwerkt → `data/export/extractie_review_feedback.md` en de extractieprompt daarop herzien (zie volgende sectie).
```bash
PYTHONPATH=. uv run python scripts/build_extraction_review_doc.py --topic stikstof --output data/export/extractie_review_stikstof.md
```
Dat genereert een documentje per argument (quote/context/stance/typology/actor) met beoordelingsinstructies voor een externe reviewer (Gemini), analoog aan `data/export/tag_quality_review.md` maar dan voor Stage 1 i.p.v. de tag-laag. Plakken in Gemini en het antwoord verwerken is bewust menselijk werk, niet geautomatiseerd zoals `import_tag_batch.py`.

### Gemini-review van de 137 arguments verwerkt: prompt verder aangescherpt

`data/export/extractie_review_feedback.md` (Gemini's beoordeling per argument + samenvattende patronen) wees op vier systematische problemen, naast de al bekende metadiscours-recall:
1. **Kale standpunten/intenties zonder onderbouwing** werden toch als argument geëxtraheerd (bv. "Ik strijd hier tot de laatste dag voor de boeren", "Afzwakking steunen we niet").
2. **Versnippering**: opeenvolgende zinnen die één punt uitwerken werden opgeknipt in meerdere losse argumenten.
3. **Typologie-inconsistenties**: overmatig gebruik van `legal` voor bestuurlijke/beleidsmatige feiten die geen wet/regelgeving zijn.
4. **Pro/contra-verwarring**: `stance` was gedefinieerd t.o.v. het abstracte onderwerp "{topic}", niet t.o.v. het beleid dat concreet ter discussie staat — leidde tot foute labels bij bv. BBB-sprekers die het eigen verleden verdedigen tegen huidig beleid.
5. **Dubbele extracties** (zelfde punt 2-3x geëxtraheerd binnen één betoog) — cross-document duplicaten (zelfde punt herhaald over meerdere sprekerbeurten) zijn hiermee bewust NIET opgelost (kan niet per-document, elke LLM-call heeft geen zicht op andere documenten) en blijven een open punt voor een latere dedup-stap.

**Beslissing (met gebruiker afgestemd via AskUserQuestion)**: `stance` wordt voortaan gemeten t.o.v. het **zittende/voorgestelde kabinetsbeleid**, niet t.o.v. het abstracte onderwerp. Om dit concreet te maken kreeg `topics` een `description`-kolom (was ongebruikt/`NULL`): een door de gebruiker/onderzoeker geschreven pro/contra-narratief per topic, ingevuld voor `stikstof` via een handmatige `UPDATE topics SET description = ...`. `extract_arguments.py` faalt nu hard (`SystemExit`) als een topic geen `description` heeft — voorkomt een stille terugval naar de oude ambigue definitie voor toekomstige topics (asielbeleid, abortus, etc.).

**Prompt-wijzigingen** (`pipeline/prompts/extract_argument.md`): expliciete "geen onderbouwing = geen argument"-regel met negatieve voorbeelden, "één punt = één argument"-regel (samenvoegen i.p.v. opknippen binnen een sprekerbeurt), aangescherpte `legal`-definitie (alleen echte wet/regelgeving/juridische procedure), en `stance` nu gedefinieerd via de nieuwe `{topic_description}`-placeholder i.p.v. het kale onderwerp.

**Geverifieerd** via `scripts/compare_models.py qwen/qwen3.6-27b --doc-ids <lijst>` (uitgebreid met een `--doc-ids`-flag, was hardcoded op 40-54): getest tegen de specifiek door Gemini gevlagde documenten (37, 56, 101, 107, 116, 122, 129, 133, 150, 167, 169, 175, 192, 218) — geen regressie op procedurele/metadiscours-gevallen, en doc 150 blijft correct 1 argument opleveren. **Nog niet kwantitatief opnieuw beoordeeld** (geen nieuwe Gemini-review-ronde gedraaid op deze wijzigingen) — dat is een logische volgende stap vóór de volle batch.

**Nog niet gedaan**: de 137 bestaande arguments in de DB zijn geëxtraheerd met de oude prompt/stance-definitie en zijn niet met terugwerkende kracht gecorrigeerd. De ~218 documenten met `extraction_attempted_at IS NOT NULL` (incl. 0-argument-gevallen) worden door de huidige skip-logica niet opnieuw verwerkt. Of je dit moet leegmaken en opnieuw draaien vóór de volle batch is nog een open beslissing.

## Antigravity CLI (`agy`) in Docker: werkend als alternatieve LLM-backend

Naast de lokale LM Studio/qwen-pipeline is `agy` (Google's Antigravity CLI, geeft toegang tot Gemini-modellen) nu bruikbaar vanuit een geïsoleerde Docker-container — bedoeld om te testen of een sterker model de extractiekwaliteit verder verbetert. Zie ook het plan-document `~/.claude/plans/om-de-accuraatheid-wat-recursive-hoare.md` voor de volledige achtergrond/afwegingen.

- **`docker/agy/Dockerfile`**: `debian:bookworm-slim` + non-root user `agy`, installeert de CLI via `curl -fsSL https://antigravity.google/cli/install.sh | bash`. Gebouwd en getest (`docker build -t bipolariteit-agy docker/agy`).
- **Auth zonder de host-Keychain aan te raken**: `agy` gebruikt geen API-key-auth (nog niet ondersteund door Google, zie hun GitHub issue #78), alleen browser-OAuth. Credentials + volledige sessiestate blijken te leven onder **`~/.gemini`** (niet `~/.config` of `~/.antigravity`, ondanks wat de naam doet vermoeden — bevestigd door dit empirisch te testen met een probe-mount over meerdere kandidaat-paden). Bind mount: `-v "$HOME/.bipolariteit/agy_gemini_config:/home/agy/.gemini"`. Eenmalige interactieve login (`docker run -it --rm -v ...:/home/agy/.gemini bipolariteit-agy agy`, moet door de gebruiker zelf gedraaid worden i.v.m. de browser-URL/code-plak-stap) volstaat; latere `docker run`s met dezelfde bind mount hergebruiken de sessie zonder opnieuw in te loggen.
- **`~/.bipolariteit/agy_gemini_config/`** bevat dus een live OAuth-token (`antigravity-oauth-token`) plus volledige sessietranscripten — bewust **buiten de repo** gehouden (verplaatst uit het voorheen gebruikte `docker/agy/gemini_config/`, vlak vóór het eerste `git init`, zodat een live token nooit binnen een version-controlled directory kan belanden, ook niet gitignored). `scripts/agy_run_batch.py`/`agy_run_tagging_batch.py`/`agy_test_tag_reasons.py` verwijzen hier nu naartoe via `AGY_GEMINI_CONFIG_DIR = Path.home() / ".bipolariteit" / "agy_gemini_config"`.
- **Non-interactieve extractie werkt**: `agy --print "<prompt>" --model <naam> --sandbox` (geen `--dangerously-skip-permissions` nodig, we vragen alleen tekstgeneratie). Geverifieerd op doc 150 (dezelfde metadiscours-testcase) met zowel `gemini-3.1-pro-low` als `gemini-3.6-flash-low`: beide leveren identieke, correcte JSON-output (1 argument, `stance: unclear`, `typology: other`). **Besluit: `gemini-3.6-flash-low` als eerste keuze** (zelfde kwaliteit op deze test, vermoedelijk sneller/goedkoper dan pro-low — latency nog niet formeel vergeleken).
- **Beschikbare modellen** (`agy models`, na login): `gemini-3.6-flash-{high,medium,low}`, `gemini-3.5-flash-{high,medium,low}`, `gemini-3.1-pro-{high,low}`, `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium`.
- **⚠️ Geen scriptbare usage/quota-check gevonden.** `/usage`, `/credits`, `/quota` bestaan alleen als interactieve TUI-commando's (bubbletea, crasht met "could not open TTY" zonder een echte terminal) — geen los CLI-subcommando, niets bruikbaars in de logs (`~/.gemini/antigravity-cli/log/*.log`, alleen "starting reload" zonder cijfers) of cache-bestanden. Gebruiker noemde een daglimiet van ~10% — dit kan alleen handmatig gecontroleerd worden door zelf `agy` interactief te starten en `/usage` te typen; geen geautomatiseerde before/after-check mogelijk zolang Google dit niet blootlegt.
- **`scripts/compare_models.py`** kreeg een `--doc-ids`-flag (zie sectie hierboven) — nog niet uitgebreid om `agy` als backend aan te roepen (draait nu alleen tegen de LM Studio/`call_llm`-pad). Logische volgende stap als `agy` serieus als backend gebruikt gaat worden.

**Nog niet gedaan / buiten scope van deze sessie**: `agy` integreren als volwaardige, herbruikbare backend-optie in `pipeline/extract_arguments.py` (naast `call_llm`'s LM Studio-pad).

### Quota-kalibratie: volle batch via `agy` past niet in één dag

Om de "geen scriptbare usage-check"-beperking hierboven te omzeilen: 20 echte extractieprompts (dezelfde 20 documenten als de Gemini-review, via nieuwe scripts `scripts/agy_prepare_batch_prompts.py` + `scripts/agy_run_batch.py`, model `gemini-3.6-flash-low`) door `agy` gedraaid, met de gebruiker die `/usage` handmatig aflas vóór en ná de run (enige beschikbare methode, zie hierboven).

**Resultaat**: 99.50% → 97.38% quota over 20 documenten = **2.12% verbruikt, ~0.106%/document**. Alle 20 calls slaagden (~5s/doc, geen lege antwoorden). Geëxtrapoleerd naar de resterende volle batch (~3949 documenten): **~419% van een dagquota** — grofweg 4-5 dagen quota nodig als die dagelijks reset, dus **niet** in één overnight run te draaien zoals de lokale qwen-setup (die kostte alleen stroom/tijd, geen quota).

**Besluit**: `agy`/Gemini wordt niet gebruikt voor de volle batch — te duur qua dagquota (zie hierboven). De volle 3949-document batch blijft draaien via de lokale qwen/LM Studio-pipeline (`pipeline/extract_arguments.py`, gratis, alleen tijd/stroom). `agy` wordt ingezet als **validatiemiddel**: steekproeven/tweede-beoordeling van de qwen-extracties, analoog aan hoe Gemini via de browser al gebruikt is voor de review van de 137 arguments (`extractie_review_feedback.md`) — maar dan gescript via de Docker-container in plaats van handmatig kopiëren/plakken. `scripts/agy_prepare_batch_prompts.py` + `scripts/agy_run_batch.py` (al gebouwd, zie hierboven) zijn hiervoor het startpunt; een volgende stap zou zijn er een `--doc-ids`-achtige flag aan toe te voegen (zoals `compare_models.py` al heeft) zodat gerichte steekproeven uit de qwen-output makkelijk via `agy` te controleren zijn, i.p.v. de nu hardcoded `DOC_IDS`-lijst.

## Tag-taxonomie: `data/tags.toml` geïntegreerd als tweede-pass tagging

Een argumentatie-onderzoeker leverde `data/tags.toml`: 4 perspectieven → oorspronkelijk 10 labelgroepen → 46 tags (`sleutel`/`beschrijving`), inmiddels uitgebreid naar 11 labelgroepen → 51 tags (zie "Metadiscussie" verderop). Was volledig ongebruikt tot nu toe. Geïntegreerd als:

- **`pipeline/db/schema.sql`**: 3 nieuwe tabellen (`labelgroepen`, `tags`, `argument_tags`, allemaal `IF NOT EXISTS` zodat ze veilig tegen de al-bestaande lokale DB toegepast konden worden), plus `documents.activiteit_soort` en `arguments.tagged_at` kolommen (via `ALTER TABLE`, éénmalig handmatig toegepast — zie hieronder). Toegepast op de echte `data/bipolariteit.db` (3949 documenten, 0 arguments op dat moment) zonder dataverlies, geverifieerd via `.schema`-diff.
- **`pipeline/db/seed_tags.py`**: laadt `tags.toml` in de DB. **Belangrijk voor toekomstige tag-updates van de onderzoeker**: dit is een two-phase sync (eerst alles `active=0`, dan alles wat nog in het bestand staat upserten naar `active=1`), niet clear+reinsert. Dus een tag-update is voortaan gewoon: onderzoeker past `tags.toml` aan → `uv run python -m pipeline.db.seed_tags` → klaar. Verwijderde/hernoemde tags worden stil (`active=0`), nooit hard verwijderd (behoudt `argument_tags`-geschiedenis, geen FK-breuk).
- **`pipeline/taxonomy.py`**: onze eigen (niet uit `tags.toml` afgeleide) inschatting van single- vs. multi-select per labelgroep (`LABELGROEP_SELECTIE`), plus welke 3 labelgroepen deterministisch afgeleid worden i.p.v. door het LLM bepaald (`DERIVED_LABELGROEPEN`: Issue Arena, Actor Type, Parlementaire Context).
- **`pipeline/tag_arguments.py`** + **`pipeline/prompts/tag_argument.md`**: nieuwe, losse tweede pass (draait na `extract_arguments.py`, laat die zelf ongewijzigd) die per argument eerst de 3 deterministische tags toekent (`created_by='derived'`, gratis, geen LLM) en dan de overige 7 labelgroepen (~33 tags) via het lokale LLM laat kiezen (`created_by='llm'`). De tag-catalogus in de prompt wordt runtime uit de DB gegenereerd (nooit hardcoded), dus een tags.toml-update komt automatisch mee in de eerstvolgende run. Idempotent via `arguments.tagged_at IS NULL` (zelfde patroon als Stage 1's bekende 0-resultaat-probleem, nu met een expliciete completion-marker i.p.v. absence-based check).
- **Parlementaire Context — nog niet volledig geverifieerd**: `ingest_tk.py` legt nu `<activiteit soort="...">` vast in `documents.activiteit_soort`. Van de 5 lokale VLOS-bestanden is alleen `"Plenair debat"` → `Context-Plenair` bevestigd (32 hits); de mapping voor Vragenuur/Commissiedebat/Wetgevingsoverleg/Tweeminutendebat in `ACTIVITEIT_SOORT_TO_CONTEXT` (`pipeline/tag_arguments.py`) is een aanname op basis van de terminologie in `docs/plan.md`, nog niet tegen echte data getest. Onbekende `soort`-waarden blijven bewust ongetagd.
- **Getest**: `uv run pytest tests/` (16 tests, incl. nieuwe `test_tags_toml.py` en `test_seed_tags.py`) + een handmatige smoke-test met gefabriceerde data (derived-tags, cardinaliteit-validatie, onbekende-sleutel-validatie) — alle drie gedragingen correct bevestigd. **Nog niet getest tegen echte LLM-output** (Stage 1 heeft nog geen enkel argument in de DB geschreven, alleen `--dry-run`-runs tot nu toe).

Gebruik:
```bash
uv run python -m pipeline.db.seed_tags [--dry-run]
uv run python -m pipeline.tag_arguments --topic stikstof --limit 15 [--min-id N] [--model ...] [--dry-run]
```

## Batch-tag-workflow via Gemini (alternatief voor `tag_arguments.py`'s one-by-one lokale LLM-calls)

`pipeline/tag_arguments.py` tagt één argument per lokale LLM-call (~30s/argument via LM Studio) — voor een handjevol argumenten prima, maar te traag om als workflow te herhalen tijdens iteratie op de taxonomie/prompt. Daarom twee nieuwe losse scripts die hetzelfde databasecontract (`argument_tags`, `arguments.tagged_at`) vullen maar via één plak-actie in een externe chat-LLM (Gemini, gebruiker heeft alleen consumer-abonnementen, zie sectie hieronder):

- **`pipeline/prepare_tag_batch.py`**: haalt ongetagde arguments op (`fetch_untagged_arguments`, zelfde functie als `tag_arguments.py` gebruikt), kent meteen de 3 deterministische tags toe (Arena/Actor-Type/Parlementaire Context — gratis, geen LLM), en schrijft één groot promptdocument weg met de taxonomie-instructies + alle argumenten + een JSON-antwoordskelet. Output plak je in Gemini.
  ```bash
  uv run python -m pipeline.prepare_tag_batch --topic stikstof --limit 40 --output data/export/tag_batch_stikstof.md
  ```
- **`pipeline/import_tag_batch.py`**: leest het geplakte Gemini-antwoord (JSON, evt. in een ```json-codeblok — `_extract_json` strippt dat), valideert per argument tegen de actieve tags-tabel (`_validate_tags`/`load_valid_tags`, hergebruikt uit `tag_arguments.py`), en schrijft geaccepteerde tags weg als `created_by='llm'` + zet `tagged_at`.
  ```bash
  uv run python -m pipeline.import_tag_batch --topic stikstof --input data/export/tag_batch_stikstof_response.json [--dry-run]
  ```

**Geverifieerd**: volledige round-trip gedraaid op de 19 op dat moment beschikbare arguments (`data/export/tag_batch_stikstof.md` → geplakt in Gemini → antwoord opgeslagen als `data/export/tag_batch_stikstof_response.json` → geïmporteerd). Resultaat: 170 `argument_tags`-rijen (38 derived + 132 llm), alle 19 arguments `tagged_at` gezet, geen import-fouten. Nog niet beoordeeld op tag-*kwaliteit* (klopt de labeling inhoudelijk) — dat is nog open, zie volgende sectie.

Deze workflow vervangt `tag_arguments.py` niet (die blijft de "echte" geautomatiseerde pad voor de uiteindelijke volle run), maar is handig voor snelle iteratie/steekproeven zolang de taxonomie/prompt nog niet definitief is.

**Bekende beperking**: `prepare_tag_batch.py --output` gebruikt een vast bestandspad, dus een tweede batch-run (bv. resterende ongetagde argumenten) overschrijft het promptbestand én -- als je hetzelfde pad voor het antwoord gebruikt -- ook het vorige Gemini-antwoord. Bij de eerste keer draaien is dit ook gebeurd: de 19 arguments zijn in twee rondes getagd (11 + 8), maar alleen het antwoordbestand van de laatste ronde (argumenten 12-19) is nog aanwezig in `data/export/`. Geen dataverlies in de DB (beide rondes zijn al geïmporteerd), wel verlies van de ruwe Gemini-respons voor argumenten 1-11 als brondocument. Voor toekomstige batches: geef `--output` een uniek pad per ronde (bv. met argument-id-range of timestamp in de bestandsnaam).

### Tag-kwaliteitscontrole (steekproef, labelgroep "Dialectische Kwaliteit")

Handmatige tweede-beoordeling uitgevoerd op 4 van de 19 getagde arguments (id 8, 15, 16, 17), via `data/export/tag_quality_review.md` (promptbestand, geplakt in Gemini als onafhankelijke tweede beoordelaar met alleen de taxonomiedefinities + volledige argumenttekst, geen kennis van wie de tag oorspronkelijk toekende).

**Resultaat: 3 van 4 correct, 1 fout gevonden — en die fout leidde tot een nieuwe labelgroep, niet alleen een tag-correctie.**
- Arg 8, 15, 16: toegekende drogreden-tags (Stropop, Ad-Hominem, Bespelen-Publiek) bevestigd als terecht.
- **Arg 17: fout, en interessanter dan een gewone misser.** Had `Drogreden-Bespelen-Publiek`, maar de tekst ("wij de plicht hebben om partijen te verwijten wat hier is misgegaan...") is geen drogreden — het is een heel ander soort uiting: een uitspraak *over* de discussie zelf (mag je dit hier zeggen), niet een inhoudelijk argument *in* de discussie. Eerste correctie (`Kwaliteit-Zuiver`) bleek ook niet juist: de uitspraak beweert een blaam-claim ("verantwoordelijk voor het slopen van de boerenstand") als vaststaand feit en gebruikt de plicht-framing om die claim aan bewijslast te onttrekken — dat is geen "schoon" argument, het is gewoon een ander fenomeen dan wat de bestaande taxonomie ving.

**Nieuwe labelgroep "Metadiscussie" toegevoegd** (`data/tags.toml`, perspectief "Filosofisch & Argumentatietheoretisch", naast Redeneerschema en Dialectische Kwaliteit) na overleg met de argumentatie-onderzoeker — brief staat in `docs/onderzoeksvraag-discussieniveau.md`, gebaseerd op het pragma-dialectische onderscheid objectniveau vs. metaniveau. 5 tags, `selectie = "enkel"` (`pipeline/taxonomy.py`): `Meta-Bevoegdheid` (wie gaat hierover), `Meta-Agenda-Tijdigheid` (is dit nu aan de orde), `Meta-Reikwijdte` (mag dit hier besproken worden / is deze bewering toelaatbaar), `Meta-Vorm-Setting` (in welke setting/vergaderformat), `Meta-Deelnemers` (wie mag meedoen). Geen `Meta-Object`-tag — afwezigheid van een Metadiscussie-tag betekent gewoon objectniveau (zelfde patroon als "null als geen enkele optie past" elders in de taxonomie). `uv run python -m pipeline.db.seed_tags` gedraaid: nu 11 labelgroepen, 51 tags in de DB (was 10/46). Arg 17 opnieuw gecorrigeerd: `Kwaliteit-Zuiver` vervangen door `Meta-Reikwijdte`.

Conclusie: batch-tagging via Gemini is grotendeels betrouwbaar op deze kleine steekproef, maar niet foutloos — en de ene fout die we vonden wees niet op een verkeerde tag-keuze binnen de bestaande taxonomie, maar op een gat in de taxonomie zelf. Een tweede-beoordelingsstap (net als hier gedaan) blijft zinvol vóór een volle batch-run. De overige labelgroepen (Framing-Focus, Morele Fundamenten, Redeneerschema, etc.) zijn nog niet los gecontroleerd, en de nieuwe Metadiscussie-labelgroep is nog nergens anders dan bij arg 17 toegepast/getest.

## LLM-provider: lokaal via LM Studio, model-keuze nog niet definitief

Lokaal via LM Studio (niet Ollama — gebruiker gebruikt MacPorts + LM Studio, niet Homebrew/Ollama), OpenAI-compatibele server op `http://localhost:1234`. Machine: Apple M2 Max, 64GB RAM. Reden voor lokaal: gebruiker heeft alleen Claude Pro/Gemini Pro (consumer-abonnementen, geen API-toegang inbegrepen), en koos voor een lokale gratis optie boven Gemini's gratis API-tier.

4 modellen lokaal aanwezig (65GB totaal), getest op reasoning-overhead met een triviale prompt ("Zeg alleen het woord: hallo"):

| model | reasoning tokens (triviale test) | opmerking |
|---|---|---|
| `qwen/qwen3.6-35b-a3b` (MoE, 22GB) | 2600+ | oorspronkelijke keuze; reasoning niet uit te zetten gebleken tot de ontdekking hieronder |
| `qwen/qwen3.6-27b` (dense, 17GB) | ~200 zonder fix, **0 mét fix** | zie hieronder — huidige default in `extract_arguments.py` |
| `google/gemma-4-31b` (dense, 19GB) | ~65 | lichte reasoning, nog niet builtin te onderdrukken getest |
| `google/gemma-4-e4b` (dense, 6GB) | 0 | instant, geen reasoning-overhead, nog niet op extractiekwaliteit getest |

**Belangrijke ontdekking: `reasoning_effort` request-parameter.** `chat_template_kwargs.enable_thinking:false` en een `/no_think`-suffix in de prompt werken **niet** bij deze Qwen3.6-modellen via LM Studio. Wat wél werkt: de top-level request-parameter `"reasoning_effort": "none"` in de `/v1/chat/completions`-payload — dit is vermoedelijk wat ook de "Reasoning effort"-toggle in de LM Studio chat-sidebar instelt. Bevestigd via curl op zowel `qwen/qwen3.6-27b` als handmatig door de gebruiker in de UI. Met deze parameter zet `qwen/qwen3.6-27b` `reasoning_tokens` naar 0 en antwoordt direct. `extract_arguments.py` gebruikt dit al standaard (`--reasoning-effort none`, override mogelijk via CLI-flag).

Starten/laden (CLI `lms`, in `~/.lmstudio/bin`, niet standaard op PATH):
```bash
export PATH="$HOME/.lmstudio/bin:$PATH"
lms server start
lms load qwen/qwen3.6-27b   # of: lms unload --all && lms load <ander model> -- pas op met meerdere grote modellen tegelijk geladen (kan "insufficient system resources" geven)
```

## Frontend v1: Astro + Vue, gebouwd op de bestaande 234 arguments

Vooruitlopend op de volle batch (zie hieronder) is een eerste werkende website gebouwd (`frontend/`, Astro + Vue, losse CSS, geen React — conform `docs/plan.md`), zodat besloten kan worden wat er nog nodig is op basis van echte data i.p.v. blind door te bouwen.

- **`pipeline/build_static_data.py`** (nieuw): exporteert `arguments` (+ `claims`, `argument_tags`) naar `data/export/topics/<slug>.json` + `topics-index.json`. Nog geen Stage 2 (redactie/opposition-linking bestaat nog niet). `uv run python -m pipeline.build_static_data --topic stikstof` opnieuw draaien na elke DB-wijziging om de export te verversen.
- **Pagina's**: `/` (topiclijst), `/topics/[slug]/` (drie kolommen pro/contra/onduidelijk — `unclear` bewust een eigen kolom, niet weggelaten, want daar landen o.a. de metadiscours-argumenten uit deze sessie), `/about/` (uitgangspunten/"we listen and we don't judge", zodat het neutraliteits-voorbehoud niet op elke pagina/kaart herhaald hoeft te worden).
- **`StatsPanel.vue`**: percentage pro/contra/onduidelijk per partij, ECharts (`vue-echarts`) met een **custom `renderItem`-series** (niet standaard bar-series — een eerdere per-partij-multi-series-aanpak voor variabele bar-dikte brak de uitlijning tussen y-as-labels en bars; custom renderItem garandeert dat bars altijd gecentreerd blijven op hun category-tick, ongeacht dikte). Bar-dikte schaalt (sqrt) met het aantal argumenten per partij. Kleuren volgen de `dataviz`-skill: diverging paar blauw/rood (pro/contra) + neutraal grijs (onduidelijk), gevalideerd i.p.v. de aanvankelijk handgekozen teal/amber.
- **Partijlogo's**: echte SVG's van Wikimedia Commons (via de Wikimedia API, niet gescrapet) voor de 16 partijen die daadwerkelijk in de data voorkomen; `PartyLogo.vue` valt terug op een simpele zwart-wit initiaal-placeholder voor eenmansfracties zonder officieel logo (Groep Markuszower, Lid Keijzer) — bewust géén verzonnen logo. "PRO" krijgt een disambiguatie-suffix ("voorheen PvdA/GroenLinks") via `lib/parties.ts`.
- **Feedback-UI**: elke `ArgumentCard` heeft een "feedback geven"-knop (verkeerde stance/typologie/geen argument/citaat klopt niet/anders + toelichting), opgeslagen in `localStorage` (bewust geen backend — site blijft statisch) met een "Feedback exporteren"-knop die alles als JSON-bestand dumpt. Periodiek handmatig te legen/verwerken.
- **Tags in de UI**: geëxtraheerde taxonomie-tags (waar aanwezig) tonen als kleine badges met dotted-underline (hover = tooltip met labelgroep + beschrijving + `reden`, zie hieronder).
- Dev server: `cd frontend && npx astro dev --background` (CLAUDE.md van het frontend-scaffold beveelt dit expliciet aan i.p.v. voorgrond-dev-server), status/logs via `astro dev status`/`astro dev logs`, stoppen via `astro dev stop`.

## Tag-kwaliteit: "Kwaliteit-Zuiver" verwijderd + `reden` per tag toegevoegd

Twee taxonomie-verbeteringen na gebruikersfeedback tijdens het bekijken van de UI:

1. **`Kwaliteit-Zuiver` verwijderd** uit `data/tags.toml` (labelgroep "Dialectische Kwaliteit") — "geen herkenbare logische fouten" is een positief kwaliteitsoordeel ("dit argument is logisch zuiver"), in tegenstelling tot de overige tags in die groep die een specifiek retorisch PATROON beschrijven (bv. "dit is een ad-hominem-constructie") zonder te oordelen of dat patroon hier terecht/overtuigend is. Botst met het "we don't judge"-kernprincipe. `uv run python -m pipeline.db.seed_tags` gedraaid: tag is nu `active=0` (soft-delete, geen dataverlies — het ene bestaande argument met deze tag behoudt 'm in zijn geschiedenis).
2. **`argument_tags.reden` toegevoegd** (schema + live-DB via eenmalige `ALTER TABLE`, zelfde patroon als eerdere kolommen): een korte, argument-specifieke onderbouwing per toegekende tag, i.p.v. alleen de generieke tag-beschrijving. Doorgevoerd in:
   - `pipeline/prompts/tag_argument.md` + de inline instructietekst in `prepare_tag_batch.py`: expliciete instructie om per tag een `reden` te geven die het specifieke tekstfragment/patroon benoemt, geen herhaling van de taxonomie-beschrijving.
   - `tag_arguments.py`: JSON-skeleton per tag is nu `{"sleutel": ..., "reden": ...}` i.p.v. een kale string (`_validate_tags` accepteert ter achterwaartse compatibiliteit ook nog kale strings uit oudere geplakte Gemini-antwoorden, dan `reden=None`). `assign_derived_tags` genereert ook voor de 3 deterministische labelgroepen een automatische reden (bv. "Afgeleid van VLOS-activiteitsoort 'Plenair debat'.").
   - `import_tag_batch.py`, `build_static_data.py` (tags-export bevat nu `reden`), `ArgumentCard.vue` (tooltip toont beschrijving + reden).
   - **Geverifieerd tegen een echt model** (`agy`/`gemini-3.6-flash-low`, zie hieronder): reden-teksten zijn daadwerkelijk argument-specifiek (citeren het exacte tekstfragment), geen kale herhaling van de tag-beschrijving.

## `agy` als tagging-validatiemiddel: tweede quota-kalibratie

Naast de eerdere extractie-kalibratie (zie hierboven, 419% dagquota voor de volle batch) is nu ook Stage 2 (tagging) via `agy` gekalibreerd, met dezelfde Docker-opzet:

- **`scripts/agy_test_tag_reasons.py`** (dry-read, geen DB-writes): eerste test op 1 argument, bevestigde dat de reden-teksten goed zijn (zie hierboven).
- **`scripts/agy_run_tagging_batch.py`** (schrijft écht naar de DB, zelfde contract als `tag_arguments.py`): batch van 20 ongetagde argumenten (id 20-39), model `gemini-3.6-flash-low`. **Resultaat: 0 fouten, 40 derived + 174 llm tags, gem. 7.0s/argument.** Quota: 85.20% → 82.12% = **3.08% voor 20 argumenten, ~0.154%/argument** — duurder dan extractie (~0.106%/document), verklaarbaar door de langere taxonomie-catalogus in de prompt en de gemiddeld 8-10 tags + redens per antwoord.
- **Bevestigt het eerdere besluit**: `agy` blijft ongeschikt voor de volle batch (zou nog slechter uitpakken dan de 419%-schatting voor extractie, gezien de hogere kost per argument), en blijft dus **validatie-only** — nu voor zowel Stage 1 als Stage 2. De volle taggingrun blijft via `pipeline/tag_arguments.py` (lokale qwen/LM Studio, gratis) lopen zodra die weer aangezet wordt.
- Na deze batch: **39/234 arguments getagd** (was 19), 384 `argument_tags`-rijen, 214 met een `reden` gevuld (de rest is historisch, van vóór dit veld bestond).

## Extractiebatch gepauzeerd (stroom/batterij), hervatbaar

De volle Stage-1-batch (`pipeline/extract_arguments.py --topic stikstof --limit 4000`, lokale qwen/LM Studio) is halverwege gestopt omdat de laptop op accu liep en de batterij laag werd — **niet** vanwege een fout. Stand bij pauzeren: **414/3949 documenten geprobeerd, 234 arguments**. Herstarten met exact hetzelfde commando pakt automatisch verder waar het gebleven was (skip-mechanisme via `extraction_attempted_at`, per-document commit dus geen corrupte state). Nog te doen zodra weer op stroom: batch hervatten/afmaken, dan `build_static_data.py` opnieuw draaien voor een verse export.

## Stage 2 gebouwd: `redactie_check.py` (balans-check + opposition-linking)

Laatste ontbrekende pipeline-stage uit `docs/plan.md`. Twee losse dingen, geen van beide een fact-check:

1. **Balans-check, deterministisch, geen LLM** — expliciete gebruikerskeuze via een vraag: een `document` hier is één sprekersbeurt van één Kamerlid, dus "is dit document eenzijdig" is triviaal altijd waar en zegt niets. In plaats daarvan: `compute_balance()` berekent de **lopende** pro/contra-verhouding van het topic-corpus, begrensd tot documenten `<= document_id` (niet de hele, nog groeiende corpus tellen — dat zou bij elke run andere getallen opleveren voor dezelfde rij, precies het tegenovergestelde van "deterministisch"). `pass_status` (balanced/imbalanced/flag) volgt uit het minderheidsaandeel (drempels 35%/15%, zie code-comment). Eén `redactie_reviews`-rij per document.
2. **Opposition-linking, wel LLM** (lokale qwen/LM Studio, zelfde contract als de andere stages) — per document met nieuwe pro/contra-argumenten wordt een steekproef van bestaande argumenten met het *tegenovergestelde* standpunt aangeleverd (willekeurig gekozen, niet "meest recente N" — anders wordt een handvol recente argumenten kunstmatig een opposition-hub, sample-artefact i.p.v. signaal), en vraagt de prompt (`prompts/redactie_bias_check.md`) alleen naar `direct_rebuttal` vs. `thematic`-koppelingen, nooit wie gelijk heeft. Geretourneerde id's worden gevalideerd tegen de aangeleverde kandidatenset (zelfde patroon als tag-sleutel-validatie in `tag_arguments.py`) — hallucinaties worden overgeslagen, niet vertrouwd.
- Idempotent via het bestaan van een `redactie_reviews`-rij per document (niet een aparte timestamp-kolom); bij een LLM-fout blijft het document bewust pending (geen rij geschreven) zodat een volgende run het herprobeert — zelfde foutafhandelingspatroon als `extract_arguments.py`.
- Getest: kleine live run + herhaalde run bevestigt idempotency (verwerkt automatisch de volgende documenten, slaat al-gereviewde over) én retry-on-error (een timeout op één document werd bij de volgende run alsnog succesvol verwerkt). `uv run pytest tests/` blijft groen.
- **Nog niet gedaan** (bewust buiten scope van deze stap): oppositions exporteren in `build_static_data.py` + een visuele koppeling tussen tegenargumenten in de frontend (plan-stap 8). Ook de volle Stage-2-batch is nog niet gestart — draait op dezelfde LM Studio-instance als de nog lopende Stage-1-batch, dus wachten tot die klaar is voorkomt onnodige GPU-contentie.

## video_url: geïmplementeerd en gedraaid

Volledig overzicht van alle TK-databronnen/API's/libraries die zijn uitgezocht (OData, SyncFeed, `tkapi`, `tkconv`, Debat Direct, tweedekamer.nl-zoeken, echokamer, OpenDataPortaal-issues) staat in **`docs/tk-data-sources-overview.md`**.

**Blocker opgelost**: de eerdere aanname dat `documents.published_at` een crawl-/fetch-timestamp was, bleek bij verificatie **onjuist** — het is al `markeertijdbegin`, een echte sprekerbeurt-timestamp uit de brontekst (geverifieerd via een directe join tussen een DB-rij en zijn exacte XML-element, exacte match). Maar `published_at` is per-sprekerbeurt, niet debat-breed. De VLOS-bron bevat het debat-brede start-/eindtijdstip rechtstreeks op `<activiteit>`-niveau (`<aanvangstijd>`/`<eindtijd>`, niet eerder opgemerkt).

- **Nieuwe kolommen** `documents.activiteit_aanvangstijd`/`activiteit_eindtijd` (schema.sql + eenmalige `ALTER TABLE` op de live DB), gevuld door `ingest_tk.py` bij nieuwe imports en met terugwerkende kracht voor alle 3949 bestaande documenten via **`scripts/backfill_activiteit_tijden.py`** (eenmalig, `document_exists`-dedup in `ingest_tk.py` zorgt dat een her-run van de ingest bestaande rijen nooit bijwerkt).
- **`pipeline/enrich_video_url.py`** (nieuw, geen LLM): groepeert documenten per activiteit (op `(activiteit_aanvangstijd, activiteit_eindtijd)`), queryt Debat Direct's zoek-API (`cdn.debatdirect.tweedekamer.nl/search?van=&tot=<debatdatum>`, gepagineerd), en kiest de kandidaat met de dichtstbijzijnde starttijd (venster: 5 min) mét een duur-ratio-sanitycheck (max. factor 2 verschil, zelfde principe als `tkconv`) om een toevallige starttijd-match op het verkeerde debat uit te sluiten. Bouwt `video_url` als `https://debatdirect.tweedekamer.nl/{debateDate}/{categoryIds[0]}/{locationId}/{slug}/video`. Idempotent via `documents.video_url IS NULL`.
  ```bash
  uv run python -m pipeline.enrich_video_url --topic stikstof [--dry-run]
  ```
- **Gedraaid en geverifieerd**: alle 8 activiteiten in de stikstof-dataset gematcht (0 zonder match), 3949/3949 documenten kregen een `video_url`, alle 8 gematchte titels komen inhoudelijk overeen met het stikstofonderwerp (bv. "Samenhangende aanpak landbouw, natuur en stikstof", "NPLG en stikstofproblematiek"). `build_static_data.py` opnieuw gedraaid: alle 478 geëxporteerde argumenten hebben nu een werkende `video_url`.
- Tests toegevoegd (`tests/test_enrich_video_url.py`: match-op-tijdvenster, duur-ratio-afwijzing, URL-opbouw). `uv run pytest tests/` blijft groen (23 tests).
- **UX-gevolg, nu opgelost**: de "bron"-link op elke `ArgumentCard` wees eerder alleen naar de ruwe OData-Verslag-resource (XML); er is nu ook een werkende video-link naast beschikbaar (frontend gebruikte `document.video_url` al, was tot nu toe altijd `NULL`).
- **Nog niet gedaan**: `activiteit_soort` staat voor alle 3949 documenten op `NULL` in de live DB (ondanks dat `ingest_tk.py` het al langer vastlegt) — losstaand van deze fix (video_url-matching gebruikt het niet), maar wel relevant voor de eerder genoemde Parlementaire-Context-tag (zie tag-taxonomie-sectie). Vermoedelijk een kolom die pas ná de laatste volle ingest is toegevoegd; behoeft een eigen backfill zoals hierboven, niet gedaan in deze sessie.

### Deep link naar het exacte spreekmoment (`?event=speaker...`)

Gebruiker wees erop dat Debat Direct ook direct naar een specifieke spreker binnen een debat kan linken: `.../{slug}?event=speaker<ISO8601-tijdstip-met-offset, url-encoded>` (naast de generieke `.../video`-link naar het begin van het hele debat).

- **`build_static_data.py`**: nieuwe `_speaker_event_url(video_url, published_at)` — bouwt deze link per argument uit de al-aanwezige `documents.published_at` (VLOS `markeertijdbegin`, zie eerder in dit document) + het debat-brede `video_url`. `published_at` is naive lokale tijd zonder offset; `zoneinfo.ZoneInfo("Europe/Amsterdam")` levert automatisch de juiste `+01:00`/`+02:00`-offset (CET/CEST), geen hardgecodeerde DST-regel nodig. Nieuw exportveld: `document.speaker_video_url`.
- **Geverifieerd**: alle 478 argumenten krijgen een `speaker_video_url`; het format matcht exact het door de gebruiker aangeleverde voorbeeld (`...T17%3A12%3A59%2B0200`). Tests toegevoegd (`tests/test_build_static_data.py`, incl. een winter-datum om de CET-offset apart te bevestigen) — `uv run pytest tests/` blijft groen (27 tests).
- **Frontend** (`ArgumentCard.vue`): toont nu "video (dit moment)" die naar `speaker_video_url` linkt (springt naar de spreker), met "video (hele debat)" (`video_url`) als fallback wanneer er om wat voor reden geen `speaker_video_url` is. Geverifieerd tegen de lopende dev-server (`localhost:4321`) — de link met `?event=speaker...` staat daadwerkelijk in de gerenderde pagina.
