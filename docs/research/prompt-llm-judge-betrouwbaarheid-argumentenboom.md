# Onderzoeksprompt: betrouwbaarheid van LLM-oordelen over argumentrelaties (issue #252)

Kopieer onderstaande prompt voor een research-georiënteerde assistent/sessie.

---

## Context

Ik bouw een site (bipolariteit.org) die politieke Kamerdebatten structureert als
"argumentenbomen": geëxtraheerde argumenten uit letterlijke Kamercitaten worden
gekoppeld via getypeerde relaties, gebaseerd op het AIF-model (Argument
Interchange Format, arg-tech.org/AIFdb; Lawrence & Reed 2019, *Argument Mining:
A Survey*, Computational Linguistics 45(4)): `support` (argument B onderbouwt
argument A) en `conflict` (argument B weerlegt argument A).

Om te voorkomen dat de selectie/koppeling een debat scheeftrekt, wilden we een
tweede LLM-pas laten beoordelen of elke voorgestelde relatie daadwerkelijk
standhoudt (een "redactiestap", losstaand van de structureerstap die de relaties
voorstelt). We hebben vier varianten hiervan getest op een echte dataset (acht
`conflict`-relaties uit een Tweede Kamerdebat over stikstofbeleid, model
`gemini-3.8-flash-medium`):

1. **Rolgebonden, tweezijdig**: een "pro-redacteur" en een "contra-redacteur"
   beoordelen elk onafhankelijk of een relatie standhoudt (`onderschrijft:
   true/false`). Bevinding: alle acht `conflict`-relaties in de dataset hadden
   toevallig dezelfde vorm (target=pro-argument, premise/aanvaller=
   contra-argument), en de pro-redacteur kende consequent "winst" toe aan het
   pro-argument, ongeacht de specifieke inhoud van elk paar — een rol-/
   labelgebonden bias, geen inhoudelijk oordeel.
2. **Neutraal (geen rol), twee categorieën** (`expliciete_verwijzing` vs.
   `logische_ondermijning`, alle 8 relaties in één call): alle acht kregen
   hetzelfde label (`logische_ondermijning`).
3. **Zelfde opzet + derde categorie** (`afweging`: "beide claims kunnen
   gelijktijdig waar zijn, andere positie op hetzelfde continuüm, geen
   tegenspraak"): weer alle acht identiek, nu allemaal `afweging` — inclusief
   een relatie die in variant 2 nog als de sterkste, meest overtuigende
   logische tegenspraak was beoordeeld.
4. **Elke relatie in een eigen, geïsoleerde call** (om een batch-/
   volgorde-effect binnen één antwoord uit te sluiten): weer alle acht
   identiek (`afweging`), met specifieke, op de content gebaseerde
   onderbouwingen per relatie (dus geen kopieer-plakwerk) maar dezelfde
   uiteindelijke classificatie.

In alle vier varianten leverde het model steeds *specifieke, plausibel
klinkende* onderbouwingen (geen generieke tekst), maar de classificatie zelf
discrimineerde niet tussen relaties. Dat sluit "prompt nog niet scherp genoeg"
of "besmetting binnen een batch-aanroep" als verklaring grotendeels uit.

## Werkhypothese

Het patroon lijkt te correleren met het soort vraag: een feitelijke/tekstuele
vraag ("citeert argument B letterlijk het punt van argument A?") lijkt
fundamenteel anders van aard dan een interpretatieve/normatieve vraag ("houdt
deze weerlegging logisch stand?" / "is dit een afweging of een tegenspraak?").
Bij politieke retoriek is vrijwel elk argumentenpaar op meerdere, onderling
onverenigbare manieren "geldig" te interpreteren — mogelijk heeft de
interpretatieve vraag daardoor geen stabiel, uit de tekst afleidbaar antwoord,
en confabuleert het model een post-hoc rationalisatie voor welk antwoord ook
maar het gemakkelijkst te beargumenteren is, in plaats van een oordeel te
vellen dat kán variëren per geval.

## Onderzoeksvragen

1. Is er literatuur over LLM-as-judge-betrouwbaarheid die specifiek onderscheid
   maakt tussen **feitelijke/verifieerbare** classificatietaken en
   **interpretatieve/normatieve** classificatietaken, en laat zien dat
   discriminerend vermogen (variantie tussen items) systematisch lager is bij
   het laatste?
2. Is dit "convergeren naar één antwoord voor alle items in een verzameling,
   met steeds specifieke maar niet-discriminerende onderbouwing" een bekend
   fenomeen (sommige termen om op te zoeken: *LLM-as-judge consistency*,
   *position/order bias*, *self-consistency*, *rationalization vs. reasoning*,
   *sycophancy toward a salient category*, *anchoring op de laatst
   geïntroduceerde/meest saillante prompt-categorie*)? Zo ja, onder welke
   omstandigheden treedt het op, en zijn er bekende tegenmaatregelen die niet
   neerkomen op "nog een categorie toevoegen" (wat in variant 3 hierboven
   juist averechts werkte)?
3. Is er onderzoek specifiek binnen **computational argumentation
   mining/argument quality assessment** (bv. rond AIF, IBM Debater/Project
   Debater, ArgQuality-datasets) naar de betrouwbaarheid van geautomatiseerde
   (LLM- of eerdere ML-)beoordeling van of een `conflict`/`support`-relatie
   "geldig" is, en welke evaluatiecriteria daar wél/niet werkten?
4. Is er onderzoek naar **menselijke inter-annotator agreement** op vergelijkbare
   taken (twee mensen beoordelen onafhankelijk of argument B argument A
   weerlegt/ondersteunt) in politiek/gepolariseerd debatmateriaal specifiek
   (niet alleen gestructureerd essay-materiaal)? Is de agreement daar zelf al
   laag, wat zou suggereren dat het probleem niet aan het LLM ligt maar aan de
   taak (geen stabiele ground truth), en het dus geen kwestie van "een beter
   model" is?
5. Is er raakvlak met theorie over **framing/pragma-dialectiek** (Van Eemeren)
   die zou voorspellen dat "houdt deze relatie logisch stand" bij politiek
   debatmateriaal principieel onderbepaald is, in tegenstelling tot bij
   formeel-logische of wetenschappelijke tekst?

## Gewenste output

Een beknopt overzicht (geen uitputtende review) van:
- relevante papers/bronnen per onderzoeksvraag, met een korte samenvatting van
  wat ze concreet zeggen over betrouwbaarheid/discriminerend vermogen;
- of onze werkhypothese (feitelijk vs. interpretatief onderscheidt
  betrouwbaarheid) steun vindt, wordt genuanceerd, of weerlegd wordt;
- praktische implicatie: is er een bekende manier om dit soort taken wél
  betrouwbaar te laten uitvoeren (bv. door de vraagstelling te herformuleren
  tot iets feitelijks/tekstueels, door meerdere modellen te combineren, door
  self-consistency-sampling, of door de taak simpelweg als niet-geautomatiseerd-
  oplosbaar te beschouwen)?
