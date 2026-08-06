# Ontwerpgids — Argumentenboom (confrontatie-as)

Onderwerp: stikstof · Ontwerp: `Argumentenboom.dc.html` · Stijl: Classical (bound design system)

---

## 1. Het idee

Twee losse bomen naast elkaar (de bestaande ECharts-opzet) laten wél de
onderbouwing zien, maar niet waar het debat over gaat: het inhoudelijke
treffen tussen een pro- en een contra-argument. Dit ontwerp draait de
compositie om.

**Eén verticale as in het midden.** Links pro, rechts contra. De as is geen
decoratie maar de pro/contra-dimensie van het onderwerp zelf.

**Deelthema als band.** De pagina is gestapeld in horizontale banden. Elke
band bevat één deelthema (bv. *Vergunningverlening*) met het scherpste
pro- en contra-argument op dezelfde hoogte, aan weerszijden van de as. Zo
lees je horizontaal het debat en verticaal de agenda.

**Onderbouwing groeit naar buiten.** Wat een argument ondersteunt ("A, want
B") hangt eronder, van de as af, aan een gestippelde tak. Diepte gaat dus
naar de marge, nooit naar het midden — het midden blijft het strijdtoneel.

**Weerlegging is een getekende lijn.** Precies het punt waarop een
boom-layout vastloopt. Zie §4.

---

## 2. Structuur van de pagina

| Zone | Inhoud |
|---|---|
| Kop | onderwerp, kicker, en de pro/contra-dimensie in één alinea (essentieel: pro/contra is relatief aan die as) |
| Legenda | pro-kleur, contra-kleur, onderbouwingstak, weerleggingslijn, telling (`29 van 1531 · 534 pro / 997 contra`) |
| Askop | `Pro` — `deelthema` — `Contra` |
| Banden 01–06 | per deelthema: pro-cluster · asetiket · contra-cluster, gescheiden door een haarlijn |
| Buiten de confrontatie | argumenten zonder tegenhanger, incl. de coördinatieve groep |
| Twijfelachtige classificaties | drie kolommen, id + huidige (foute) stance + reden |
| Colofon | herkomst van de data en het voorbehoud bij de labels |
| Detailpaneel | sticky rechterkolom, 372px |

---

## 3. Knopen

Drie soorten, met een duidelijk verschil in gewicht:

- **Hoofdknoop** (336px) — omkaderd, licht vlak (`--color-neutral-100`), 2px
  regel bovenaan in de standpuntkleur. Draagt het deelthema.
- **Onderbouwing** (288px) — omkaderd, transparant, geen kleurregel; hangt
  aan de gestippelde tak. Lichter dus ondergeschikt.
- **Verwijskaart** — gestippeld kader, gouden rand: geen argument maar een
  wegwijzer naar een knoop die elders in de boom hangt.

Inhoud van een knoop, van boven naar beneden: `typologie` + `#id` (klein,
uppercase, tabulaire cijfers) → `gist` (Cormorant, 20px / 16,5px) →
`spreker (partij)` → optioneel het citaat → weerleggingsmarkering.

Pro-knopen zijn rechts uitgelijnd, contra-knopen links: de tekst kijkt naar
de as toe.

---

## 4. Weerleggingen — het kernprobleem

Een weerlegging loopt dwars door beide bomen heen en is daarom in een
boom-layout niet te tekenen. Hier wel, omdat de banden de twee kanten op
gelijke hoogte brengen:

- **Binnen een band** — een gestippelde gouden lijn recht over de as, van de
  rechterrand van de pro-knoop naar de linkerrand van de contra-knoop, met
  een ↔-medaillon in het hart van de as.
- **Tussen banden** (bv. #149 hangt onder deelthema 02, maar wordt weerlegd
  in deelthema 06) — de lijn wordt via de **linkermarge** omgeleid: hij
  verlaat de knoop naar links, loopt met afgeronde hoeken langs de rand
  omlaag, en komt horizontaal binnen op de verwijskaart in de doelband. Hij
  loopt dus nooit door de as met de deelthema-etiketten heen.
- **Alle medaillons staan op één verticaal** in het midden van de as, ook bij
  een gebogen lijn (de bocht is een S-curve met haar middelpunt exact op de
  as).
- Lijnen worden **gemeten uit de echte kaartposities** (na het laden van de
  fonts en bij elke hoogteverandering), niet uit vaste coördinaten. Ze
  blijven dus kloppen als citaten of onderbouwing aan/uit gaan.

Anker: elke lijn vertrekt op *kaartbovenkant + 22px* aan beide zijden, zodat
paren exact horizontaal lopen.

---

## 5. Interactie

- **Klik knoop** → detailpaneel: letterlijk citaat, spreker + partij,
  typologie, genoemde claims, weerlegging (klikbaar, springt naar de
  tegenhanger), tags.
- **Hover / selectie** → de bijbehorende weerleggingslijn verdikt naar 2px
  en verdonkert; de tegenhanger krijgt een gouden ring. Zo zie je het
  verband zonder te klikken.
- **Nogmaals klikken** deselecteert; het paneel toont dan de leesinstructie.
- Alle states komen uit de accent-ramp van het design system; geen
  browser-defaults.

---

## 6. Visuele taal (Classical + data-semantiek)

Alle waarden komen uit de tokens van het design system (`var(--*)`);
uitzondering zijn de twee standpuntkleuren, die dragen betekenis:

| Rol | Waarde | Toepassing |
|---|---|---|
| Pro | `#1f6f66` | 2px regel bovenaan de hoofdknoop, askop |
| Contra | `#9c3b32` | idem |
| Weerlegging | `--color-accent` ramp (400 / 800) | gestippelde lijn + medaillon |
| Onderbouwing | `--color-neutral-400` | gestippelde tak |
| Structuur | `--color-divider` | bandscheidingen, kaderlijnen, de as |

Kleur wordt uitsluitend als **lijn** toegepast, nooit als vlak — conform
Classical. Type: Cormorant Garamond voor gists en koppen, Lora voor lopende
tekst; cijfers tabulair (`tnum`) waar ze als data staan (ids, tellingen,
deelthemanummers).

De standpuntkleuren zijn overgenomen uit het bestaande "Ink & Rust"-palet
van de site, zodat de boom niet uit de toon valt bij de rest van
bipolariteit.nl.

---

## 7. Wat het datamodel moet leveren

Per **argument**:

| Veld | Nodig voor |
|---|---|
| `id` | knooplabel, verwijzingen, deduplicatie |
| `citaat` | detailpaneel (leidend boven het label) |
| `gist` (max 3-4 woorden) | knooplabel |
| `spreker`, `partij` | knoop + paneel (partij ook voor logo's) |
| `typologie` | knoopkicker |
| `tags[]` | paneel |
| `claims[]` | paneel, sectie "genoemde claims" |
| `stance` | zijde van de as |
| `children[]` | onderbouwing (subordinatief) |
| `twijfelachtig` + reden | sectie onderaan |

Per **groep / band**:

| Veld | Nodig voor |
|---|---|
| `deelthema` (neutraal, max ~6 woorden) | asetiket van de band |
| `pro_node`, `contra_node` | de twee zijden |
| `coordinatief.label` + `arguments[]` | coördinatieve groep (beugel) |
| `oppositions[]` (`a_id`, `b_id`, `type`) | de getekende weerleggingslijnen |

Let op: een oppositie kan tussen knopen op **verschillende diepte en in
verschillende banden** liggen. Het model moet dat toestaan; de weergave
handelt het af met de margeroute + verwijskaart.

---

## 8. Instelbaar (tweaks)

- `toonCitaten` — citaat direct in de knoop tonen (default uit).
- `toonOnderbouwing` — de subordinatieve laag verbergen; levert een strak
  overzicht van alleen de confrontaties (default aan).
- `toonTwijfel` — de sectie twijfelachtige classificaties tonen (default aan).

---

## 9. Bekende beperkingen en vervolgvragen

1. **De brondata is ruw.** Meerdere `gist`-waarden in
   `stikstof-gemini-tree.json` dekken hun citaat niet (o.a. #1195, #1146,
   #1285, #1157). Het ontwerp maakt dat zichtbaar door het citaat één klik
   ver te zetten, maar de data moet gevalideerd worden voordat dit live kan.
2. **Schaal.** De opzet is ontworpen op 6 deelthema's × 2 zijden. Bij meer
   banden is een deelthema-index of ankernavigatie in de kop nodig.
3. **Breedte.** De confrontatie-as heeft een harde minimumbreedte
   (≈1360px incl. paneel); daaronder scrollt de pagina horizontaal. Voor
   mobiel is een aparte compositie nodig — waarschijnlijk band-per-band,
   gestapeld pro boven contra.
4. **Partijlogo's** zijn nog niet ingezet; de vierkante 160×160-iconen passen
   in de knoopregel naast de spreker.
5. **Donker thema** is nog niet uitgewerkt; de twee standpuntkleuren hebben
   in "Ink & Rust" al een donkere variant.
