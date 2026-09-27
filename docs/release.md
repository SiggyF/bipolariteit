# Preview-release publiceren

Een release is een git-tag. Die tag wordt een subdomein:

| git-tag | URL |
| --- | --- |
| `v0.3.0` | `https://v0-3-0-preview.bipolariteit.org` |
| `v0.4.0-kaart` | `https://v0-4-0-kaart-preview.bipolariteit.org` |

Punten worden streepjes, want een punt zou er een extra niveau van maken — en
daar reikt het gratis certificaat niet (zie [Waarom deze URL-vorm](#waarom-deze-url-vorm)).

## Hoe het in elkaar zit

De site is volledig statisch: `frontend/dist` is een map met HTML, JS en
afbeeldingen. Er draait geen server en er is geen database nodig om te bouwen —
de frontend importeert `data/export/*.json`, en die bestanden staan in git.

De onderdelen:

- **Cloudflare Workers** — de hostingdienst. De map wordt geüpload en wereldwijd
  geserveerd. Gratis voor dit formaat.
- **`deploy/worker.js`** — een paar regels code die elk antwoord
  `X-Robots-Tag: noindex, nofollow` meegeven. Dit is ook de plek waar later
  echte toegangscontrole kan komen.
- **Wrangler** — het commandoregel-programma van Cloudflare (`npx wrangler`).
  Het uploadt de map en maakt het DNS-record en het certificaat zelf aan. Je
  hoeft het nooit met de hand te typen; de GitHub Action roept het aan.
- **`make release TAG=v0.3.0`** — bouwt de frontend en roept
  `scripts/release_preview.py` aan; dat script zet de tag om naar een hostnaam,
  schrijft `robots.txt`, rendert de wrangler-config en start de deploy.
- **`.github/workflows/release-preview.yml`** — draait dat alles bij een
  tag-push.

## Eenmalige inrichting

Dit hoef je maar één keer te doen.

### 1. API-token aanmaken in Cloudflare

Een API-token is een wachtwoord waarmee GitHub namens jou mag deployen.

1. Ga naar <https://dash.cloudflare.com/profile/api-tokens>.
2. **Create Token**.
3. Kies het sjabloon **Edit Cloudflare Workers** → **Use template**, of bouw
   een custom token met precies deze vier regels:

   | Scope | Onderdeel | Recht |
   | --- | --- | --- |
   | Account | Workers Scripts | Edit |
   | Zone | Workers Routes | Edit |
   | Zone | DNS | Edit |
   | Zone | SSL and Certificates | Edit |

   Let op de scope-kolom: elke permissieregel begint met een dropdown
   `Account` / `Zone` / `User`. **Workers Scripts** bestaat alleen onder
   `Account`; **Workers Routes** alleen onder `Zone`. Staat de eerste dropdown
   op `Account`, dan is `Workers Routes` niet eens zichtbaar in de tweede lijst
   — dat is het makkelijkst te missen punt van dit hele stappenplan.

   De laatste drie zijn er omdat `custom_domain: true` méér doet dan een script
   uploaden: de route koppelen (Workers Routes), het subdomein-record aanmaken
   (DNS) en het certificaat laten uitgeven (SSL).

4. Beperk onder **Zone Resources** tot `bipolariteit.org`, en onder
   **Account Resources** tot je eigen account.
5. **Continue to summary** → **Create Token**.
6. **Kopieer de token nu** — hij is daarna niet meer op te vragen.

> Bewerk je een bestaande token, vergeet dan niet onderaan op **Update token**
> te drukken. Zonder die klik worden de aangevinkte rechten niet opgeslagen en
> blijf je dezelfde `Authentication error [code: 10000]` zien.

> De twee extra rechten staan niet als zodanig in de Cloudflare-documentatie;
> ze zijn afgeleid uit wat `custom_domain: true` doet (een DNS-record aanmaken
> en een certificaat laten uitgeven).
>
> Loopt de eerste deploy stuk op een 403 of een authenticatiefout, maak dan
> **geen nieuwe token aan**: ga terug naar
> <https://dash.cloudflare.com/profile/api-tokens>, klik op de bestaande token
> → **Edit**, en voeg het ontbrekende recht toe. De secret in GitHub hoeft dan
> niet vervangen te worden. Cloudflare noemt in zo'n fout vaak alleen een
> foutcode; ga af op wat er misging — het uploaden van de Worker (dan mist
> *Workers Scripts*) of het aanmaken van het subdomein (dan mist *DNS* of
> *SSL and Certificates*).

### 2. Account-ID opzoeken

Op <https://dash.cloudflare.com> → klik op `bipolariteit.org` → rechts in de
kolom **API** staat **Account ID**. Kopieer die.

### 3. Beide als secret in GitHub zetten

Ga naar
<https://github.com/SiggyF/bipolariteit/settings/secrets/actions> →
**New repository secret**, twee keer:

| Naam | Waarde |
| --- | --- |
| `CLOUDFLARE_API_TOKEN` | de token uit stap 1 |
| `CLOUDFLARE_ACCOUNT_ID` | het ID uit stap 2 |

## Een release uitbrengen

```sh
make export          # ververst data/export/*.json uit de lokale database
git add data/export
git commit -m "Export voor v0.3.0"
git push

git tag v0.3.0
git push origin v0.3.0
```

De Action bouwt de frontend en publiceert. De URL staat in de samenvatting van
de run op <https://github.com/SiggyF/bipolariteit/actions>.

`make export` is de enige stap die de lokale database nodig heeft. Vergeet je
hem, dan publiceert de release simpelweg de JSON die al in git stond — de build
faalt niet. Controleer dus dat de export in de commit zit vóór je tagt.

### Handmatig, vanaf je laptop

Kan ook, bijvoorbeeld om te testen zonder een tag te maken:

```sh
export CLOUDFLARE_API_TOKEN=...
export CLOUDFLARE_ACCOUNT_ID=...

make release-dry TAG=v0.3.0   # bouwt en toont hostnaam + config, publiceert niet
make release TAG=v0.3.0       # bouwt en publiceert
```

Beide targets bouwen de frontend zelf; `make build` vooraf hoeft niet.

Het script weigert te draaien zonder die twee variabelen, ook als je lokaal al
met `npx wrangler login` bent ingelogd. Dat is expres: die inlogsessie heeft
veel ruimere rechten dan de CI-token, dus een lokale deploy zou kunnen slagen
terwijl de token in GitHub rechten mist — en dan ontdek je dat pas bij de
volgende tag. Haal die controle er dus niet uit.

## Waarom deze URL-vorm

Cloudflare geeft gratis een certificaat (Universal SSL) uit voor het domein
zelf en voor alles wat er één niveau onder zit: `*.bipolariteit.org`. Twee
niveaus diep — `v0-3-0.preview.bipolariteit.org` — valt daar buiten en vereist
een betaalde certificaat-optie (Total TLS of een Advanced Certificate). Zonder
dat krijgt een bezoeker een beveiligingswaarschuwing.

Vandaar `v0-3-0-preview.bipolariteit.org`: het woord "preview" staat er nog
steeds in, maar als streepje in plaats van als punt, dus het blijft één niveau.

`bipolariteit.org` zelf en `www` blijven vrij voor de publieke site later.

## Openbaar, maar geen officiële publicatie

Een release is gewoon bereikbaar voor wie de URL heeft — er zit geen wachtwoord
op, en dat is een bewuste keuze: het moet makkelijk zijn om mee te laten kijken.
Wat het níét is, is een officiële publicatie. Dat wordt op drie plekken
afgedwongen:

1. **Een balk boven aan elke pagina**: "Ontwikkelversie v0.3.0 — geen officiële
   publicatie." Komt uit `frontend/src/components/SiteNav.astro`, die op alle
   pagina's staat.
2. **Een uitgebreidere toelichting op `/over`** — waarom de cijfers kunnen
   schuiven en waarom je deze versie niet als bron moet citeren.
3. **Niet indexeerbaar**: `robots.txt` (geschreven door het releasescript) én
   de `X-Robots-Tag: noindex, nofollow`-header uit `deploy/worker.js`. Die
   tweede is er omdat niet elke crawler zich aan `robots.txt` houdt.

> De header hangt aan `run_worker_first: true` in de wrangler-config. Zonder
> die instelling serveert Cloudflare een bestaand bestand rechtstreeks en wordt
> de Worker helemaal niet aangeroepen — de header ontbreekt dan op precies de
> pagina's waar hij nodig is, en niets faalt. Controleer na een deploy dus
> altijd de header zelf, niet alleen of de pagina laadt:
>
> ```sh
> curl -sI https://v0-3-0-preview.bipolariteit.org/ | grep -i x-robots-tag
> ```

De hostnaam zelf is overigens sowieso niet geheim: zodra Cloudflare het
certificaat uitgeeft verschijnt hij in de openbare
[Certificate Transparency](https://certificate.transparency.dev/)-logs. Reken er
dus niet op dat een release onvindbaar blijft; reken erop dat hij herkenbaar is
als ontwikkelversie.

### De vlaggen

| Variabele | Effect |
| --- | --- |
| `PUBLIC_RELEASE_TAG` | Versienummer in de balk. Wordt door `make release` gezet. |
| `PUBLIC_RELEASE_OFFICIEEL=true` | Verbergt balk én `/over`-sectie. |

De balk is **fail-open**: hij verschijnt tenzij een build zichzelf expliciet
als officieel bestempelt. Vergeet je de vlag bij een echte publicatie, dan staat
er ten onrechte "ontwikkelversie" — vervelend, maar de omgekeerde fout (een
ontwikkelversie die zich als officieel voordoet) is veel erger.

Let op dat `PUBLIC_RELEASE_TAG` bij het **bouwen** meegegeven moet worden, niet
bij het deployen: Astro bakt de balk in de HTML. `make release` doet dat goed;
`make build` gevolgd door het script rechtstreeks aanroepen niet.

## Opruimen

Elke release is een aparte Worker (`bipolariteit-v0-3-0-preview`). Ze stapelen
op. Een oude weghalen:

```sh
npx wrangler delete --name bipolariteit-v0-3-0-preview
```

Dat verwijdert de Worker; het DNS-record moet je in het dashboard opruimen
(**DNS** → **Records**).

# Publieke release naar www.bipolariteit.org

Naast de tag-previews hierboven is er één vaste publicatie:
`www.bipolariteit.org`, de publieke site. Zie [issue #44](https://github.com/SiggyF/bipolariteit/issues/44).

Belangrijkste verschillen met een preview:

| | Preview | www |
| --- | --- | --- |
| Trigger | git-tag push | elke push naar `main` |
| Hostnaam | `<tag>-preview.bipolariteit.org` | vast: `www.bipolariteit.org` |
| Worker | `deploy/worker.js`, zet `X-Robots-Tag: noindex` | geen Worker-script, alleen statische assets |
| `robots.txt` | schrijft `Disallow: /` | geen `robots.txt` — indexeerbaar |
| Build-vlag | `PUBLIC_RELEASE_TAG=<tag>` | `PUBLIC_RELEASE_OFFICIEEL=true` |
| Ontwikkelbalk | zichtbaar | verborgen (zie `PUBLIC_RELEASE_OFFICIEEL` bij [De vlaggen](#de-vlaggen)) |

`www` volgt dus automatisch elke push naar `main` — er is bewust geen aparte
tag- of releasestap. Dat betekent dat wat er live staat op
`www.bipolariteit.org` altijd gelijk is aan de laatste commit op `main`.

## Eenmalige inrichting

Bovenop de token/account-ID-stappen hierboven ([Eenmalige
inrichting](#eenmalige-inrichting)), die voor beide releasepaden gelden, is er
één extra handmatige stap: een redirect van de kale apex naar `www`.

1. Ga naar <https://dash.cloudflare.com> → `bipolariteit.org` → **Rules** →
   **Redirect Rules** → **Create rule**.
2. Match: hostname equals `bipolariteit.org` (zonder `www`).
3. Then: **Dynamic** → `concat("https://www.bipolariteit.org", http.request.uri.path)`,
   status **301**.
4. Deploy.

Zonder deze stap serveert de kale apex niets (er is geen Worker-route voor
`bipolariteit.org` zelf, alleen voor `www`), en krijgt een bezoeker die naar
`bipolariteit.org` gaat een foutpagina in plaats van een redirect.

## Een release uitbrengen

Gebeurt automatisch bij elke push naar `main` via
`.github/workflows/release-www.yml`. Handmatig, bijvoorbeeld om te testen:

```sh
export CLOUDFLARE_API_TOKEN=...
export CLOUDFLARE_ACCOUNT_ID=...

make release-www-dry   # bouwt en toont de config, publiceert niet
make release-www       # bouwt en publiceert naar www.bipolariteit.org
```

## Toegang

De site is bij deze eerste release meteen publiek, zonder wachtwoord — net
als de previews, maar dan wél indexeerbaar. Toegangscontrole kan later nog
toegevoegd worden op dezelfde plek als bij de previews genoemd
(`deploy/worker.js` resp. een eigen worker voor www).

## Controle op publiek gelekte bestanden

De site is volledig statisch: alles in `frontend/dist` wordt letterlijk
geserveerd. `scripts/check_public_exposure.py` controleert na elke deploy
(als stap in `release-www.yml`) twee dingen:

1. Dat `frontend/dist` geen bestanden bevat die daar niet in horen —
   `.env`-bestanden, databases, sleutels, `.git`, `.claude`, `.devcontainer`.
2. Dat een lijst bekende gevoelige paden (`/.env`, `/.git/config`,
   `/wrangler.generated.jsonc`, `/.claude/settings.json`, ...) op de live
   hostnaam allemaal 404 geven.

Los draaien, tegen een willekeurige hostnaam (ook een preview):

```sh
uv run python scripts/check_public_exposure.py www.bipolariteit.org
# of, zonder frontend/dist lokaal:
uv run python scripts/check_public_exposure.py www.bipolariteit.org --skip-dist-scan
```

Dit is een sanity-check, geen volledige security-audit: de lijst gevoelige
paden is niet uitputtend, en een `200` op een pad dat er niet op staat wordt
niet gedetecteerd.

# Argumentdata publiceren (issue #163)

Perspectief-, onderwerp- en tagpagina's aggregeren over (een deel van) de
volledige argumentenset. Die als Astro-prop in de HTML bakken duwde sommige
pagina's tot 25+ MB (de Cloudflare Workers-assetlimiet is 25 MiB per bestand)
en groeit onbegrensd mee met de dataset. In plaats daarvan wordt een lean,
al-gefilterd JSON-bestand per pagina-instantie apart gepubliceerd en
client-side gefetcht (`onMounted` in bv. `PerspectiefView.vue`).

## Hoe het in elkaar zit

- **`frontend/scripts/export_public_data.ts`** — leest `data/export/topics/*.json`
  en schrijft per perspectief, per onderwerp en per tag een JSON-bestand naar
  `data/export/gepubliceerd/`. De perspectiefbestanden zijn lean-gestript
  (`toLeanArgument`, `frontend/src/lib/leanArgument.ts` — perspectiefpagina's
  tonen nooit een losse `ArgumentCard`); de onderwerp- en tagbestanden zijn
  ongestript, want `TopicView.vue`/`TagDetail.vue` renderen wél volledige
  `ArgumentCard`s (videolinks, quote_context, claims, tag-`reden`).
- **`data/export/gepubliceerd/`** is een **git submodule** op de publieke repo
  <https://github.com/bipolariteit/bipolariteit-data> (zie `.gitmodules`). De
  hoofdrepo (`SiggyF/bipolariteit`) blijft privé; alleen deze afgeleide data
  — die toch al publiek in de site zelf zit — staat los en publiek.
- **`scripts/publish_data.py`** commit + pusht wijzigingen in die submodule en
  leegt daarna de jsDelivr-cache voor de gewijzigde bestanden.
- **jsDelivr's GitHub-CDN** (`cdn.jsdelivr.net/gh/bipolariteit/bipolariteit-data@main/...`)
  serveert de bestanden client-side, met `Access-Control-Allow-Origin: *` —
  geen eigen hosting, geen custom domain, geen creditcard nodig. Werkt alleen
  tegen publieke repo's.
- Astro-pagina's geven de databasis-URL door als `dataBaseUrl`-prop, default
  `import.meta.env.PUBLIC_DATA_BASE_URL ?? "https://cdn.jsdelivr.net/gh/bipolariteit/bipolariteit-data@main"`
  (zie bv. `[naam].astro`).

R2 (Cloudflare) is eerder overwogen maar afgewezen: het vereist een
creditcard om te activeren, ook binnen de gratis tier. Zenodo is ook
overwogen (DOI/archivering) maar past niet bij een "overschrijf de huidige
data"-flow met live browser-fetch -- vandaar de Hugging Face-route hieronder
voor precies dat geval.

### Grote bestanden -> Zenodo (archief) + Hugging Face (live data), niet jsDelivr

De volle-dataset-tegelpyramide van de plenaire kaart (issue #281,
`data/export/plenair-map/plenair-map-full.pmtiles`, ~1,25 GiB, plus
`plenair-map-full.json`, ~119 MiB) is te groot voor git/GitHub (100 MB
harde bestandslimiet) en hoort dus niet in `data/export/gepubliceerd/` zoals
hierboven.

**Sinds issue #316 geldt dat ook voor de kleine variant** (`plenair-map.pmtiles`,
~50 MiB): pmtiles hoort principieel bij Hugging Face, niet bij de compacte
jsDelivr-hosting, ook al zou hij onder jsDelivr's bestandslimiet blijven.
`TiledPlenairMap.vue` fetcht 'm via een losse `tilesBaseUrl`-prop
(`resolveTilesBaseUrl()` in `frontend/src/lib/dataBaseUrl.ts`), naast de
gewone `dataBaseUrl` voor de rest van de submodule-data. `make tiles`
schrijft het bestand zoals altijd naar `data/export/plenair-map/`
(alle plenair-map-exportbestanden bij elkaar, issue #316, i.p.v. los
tussen de rest van `data/export/`); `make publish-tiles` publiceert het
naar dezelfde HF-dataset-repo als `publish-huggingface` hieronder.

In plaats daarvan gaat dit soort grote data naar twee bestemmingen met een
losse rol (besluit uit issue #293), zelfde bronbundel, geen van beide
vervangt de ander:

- **Zenodo** is het archief: DOI/versionering, voor QGIS-inspectie en de
  A0-printposter (issue #215) -- niet de interactieve site.
- **Hugging Face** is de live-databron: bestanden worden direct
  overschreven, zonder aparte publiceerstap, en zijn zo geschikt om de
  interactieve kaart tegen te laten fetchen (bevestigd: CORS + HTTP Range
  werken op HF's dataset-CDN voor bestanden van deze grootte, issue #293) --
  iets wat jsDelivr/git boven de 100 MB-limiet niet kan.

```sh
make tiles-full            # bouwt de tegelpyramide + bundelt companions in data/export/plenair-map/bundel/
make publish-zenodo        # uploadt alles in data/export/plenair-map/bundel/ als nieuwe Zenodo-versie (draft, ZENODO_TOKEN nodig)
make publish-huggingface   # uploadt dezelfde bundel als live data naar een publieke HF-dataset-repo (HUGGINGFACE_TOKEN nodig)
```

`data/export/plenair-map/bundel/` (gitignored) is de expliciete bundel-map:
`tiles-full` schrijft `plenair-map-full.pmtiles`/`-grid.json` er
rechtstreeks in en kopieert
`plenair-map-full.json`/`-clusters-full.json`/`-hierarchy-full.json` erbij,
zodat beide publiceerstappen zonder losse bestandenlijst gewoon alles
daarin publiceren -- ze kunnen zo niet uit de pas lopen over welke
bestanden erbij horen (gedeeld tussen Zenodo én Hugging Face, vandaar de
neutrale naam `bundel/` in plaats van `zenodo/`, issue #316).

`scripts/publish_zenodo.py` maakt alleen een **draft** aan (nieuwe versie,
bestanden geüpload). Publiceren zelf (onomkeerbaar, eigen DOI per versie)
blijft een bewuste, handmatige stap in de Zenodo-UI -- zelfde terughoudende
patroon als hierboven bij `publish-data`.

`scripts/publish_huggingface.py` heeft dat tussenstapje niet: de bestanden
staan meteen live op
`https://huggingface.co/datasets/SiggyF/bipolariteit-pmtiles/resolve/main/<submap>/<bestandsnaam>`
zodra het script klaar is (`<submap>` = `--repo-subdir`, default
`plenair-map` — één submap per dataset in deze repo, niet alles plat naast
elkaar), zelfde "overschrijf de huidige data"-flow als `publish-data`'s
jsDelivr-route.

**Besluit issue #293 (2026-09-27)**: `TiledPlenairMap.vue` fetcht de
**volle** dataset (`plenair-map-full.pmtiles`/`-grid.json`/`-clusters-full.json`,
~385 MiB), niet de kleine steekproef -- elke bezoeker downloadt dus de volle
tegelpyramide. De kleine variant (`plenair-map.pmtiles`, `make tiles`/
`make publish-tiles`) blijft bestaan voor snelle iteratie tijdens
ontwikkelen, maar is geen frontend-pad meer. Publicatie van de volle
variant gaat sindsdien ook via `--repo-subdir plenair-map` (consistent met
de kleine variant), niet meer los op de repo-root zoals de eerdere ad-hoc
publish uit issue #259.

## Data publiceren

```sh
make export            # SQLite -> data/export/topics/*.json (lokale DB nodig)
make publish-data       # export_public_data.ts + commit/push van de submodule
```

Losgekoppeld van een frontend-release: `publish-data` draai je handmatig,
alleen als de onderliggende dataset verandert, niet automatisch in CI. Een
`make build`/`make release*` na een `make export` zonder `make publish-data`
publiceert gewoon de frontend tegen de data die al op jsDelivr staat — die
kunnen dus tijdelijk uit de pas lopen; niet fataal (het is dezelfde export,
alleen een oudere versie), maar wel iets om aan te denken bij grote
dataset-wijzigingen.

## Lokale dev

`make dev` fetcht in DEV-mode `/data`, geserveerd door de sirv-middleware in
`astro.config.mjs` over de lokaal uitgecheckte `data/export/gepubliceerd/`-
submodule (zie `frontend/src/lib/dataBaseUrl.ts`) — geen mock/proxy, geen
netwerkverkeer naar jsDelivr nodig. Lokale wijzigingen aan
`pipeline/build_static_data.py`'s outputvorm zijn dus pas zichtbaar in dev
ná een `make export-public-data`-run (die de submodule-werkboom ververst;
`make publish-data` is pas nodig om diezelfde wijziging ook naar de live
site en andere machines te krijgen).
