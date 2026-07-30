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
3. Kies het sjabloon **Edit Cloudflare Workers** → **Use template**.
4. Dat sjabloon dekt het uploaden van de Worker, maar niet het aanmaken van het
   DNS-record en het certificaat die bij een eigen subdomein horen. Voeg onder
   **Permissions** daarom twee regels toe:

   | Scope | Onderdeel | Recht |
   | --- | --- | --- |
   | Zone | DNS | Edit |
   | Zone | SSL and Certificates | Edit |

5. Beperk onder **Zone Resources** tot `bipolariteit.org`, en onder
   **Account Resources** tot je eigen account.
6. **Continue to summary** → **Create Token**.
7. **Kopieer de token nu** — hij is daarna niet meer op te vragen.

> De twee extra rechten staan niet als zodanig in de Cloudflare-documentatie;
> ze zijn afgeleid uit wat `custom_domain: true` doet (een DNS-record aanmaken
> en een certificaat laten uitgeven). Loopt de eerste deploy stuk op een
> permissie-fout, dan noemt wrangler in de foutmelding welk recht ontbreekt.

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

## Waarom deze URL-vorm

Cloudflare geeft gratis een certificaat (Universal SSL) uit voor het domein
zelf en voor alles wat er één niveau onder zit: `*.bipolariteit.org`. Twee
niveaus diep — `v0-3-0.preview.bipolariteit.org` — valt daar buiten en vereist
een betaalde certificaat-optie (Total TLS of een Advanced Certificate). Zonder
dat krijgt een bezoeker een beveiligingswaarschuwing.

Vandaar `v0-3-0-preview.bipolariteit.org`: het woord "preview" staat er nog
steeds in, maar als streepje in plaats van als punt, dus het blijft één niveau.

`bipolariteit.org` zelf en `www` blijven vrij voor de publieke site later.

## Hoe privé is dit precies

De preview is **niet met een wachtwoord afgeschermd**. De URL is het enige dat
hem beschermt, en dat is een zwakkere garantie dan het klinkt:

- Zoekmachines worden geweerd via `robots.txt` én de `X-Robots-Tag`-header.
- Maar: zodra Cloudflare het certificaat uitgeeft, wordt de hostnaam binnen
  enkele minuten gepubliceerd in de openbare
  [Certificate Transparency](https://certificate.transparency.dev/)-logs. Die
  worden continu uitgelezen. De hostnaam is dus vindbaar, ook al is de inhoud
  niet geïndexeerd.
- En de tagnaam is te raden voor wie het project kent.

Voor een échte afscherming is Cloudflare Access de volgende stap (gratis tot 50
gebruikers, inloggen met een code per e-mail). `deploy/worker.js` is de plek
waar dat inhaakt.

## Opruimen

Elke release is een aparte Worker (`bipolariteit-v0-3-0-preview`). Ze stapelen
op. Een oude weghalen:

```sh
npx wrangler delete --name bipolariteit-v0-3-0-preview
```

Dat verwijdert de Worker; het DNS-record moet je in het dashboard opruimen
(**DNS** → **Records**).
