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
2. **Een uitgebreidere toelichting op `/about`** — waarom de cijfers kunnen
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
| `PUBLIC_RELEASE_OFFICIEEL=true` | Verbergt balk én `/about`-sectie. |

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
