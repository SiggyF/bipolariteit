# Design-pakket: A0-printkaart van de plenaire/debattenkaart

## Doel

[Issue #215](https://github.com/SiggyF/bipolariteit/issues/215) vraagt om
een hoge-resolutie PDF-export van de plenaire/debattenkaart, bedoeld als
marketingmateriaal (op A0 afdrukbaar, om op te hangen in de Tweede Kamer).
Dit is een VROEGE fase-1-preview om een visuele richting te kunnen bespreken
-- geen kant-en-klaar eindontwerp. We werken in korte cycli: dit is de eerste
ronde, gericht op stijlkeuzes (kleur, dichtheid, hoe de clusterhiërarchie
leesbaar te maken), niet op de uiteindelijke print-kwaliteit render (die komt
later uit `datashader`/QGIS, zie `docs/handoff.md`).

## Waar dit over gaat

De kaart toont ~135.000 sprekersbijdragen uit Tweede Kamerdebatten,
gepositioneerd via UMAP (dimensiereductie op tekst-embeddings) zodat
inhoudelijk vergelijkbare bijdragen dicht bij elkaar liggen. Vier
onderwerpen zijn gecureerd/gelabeld (stikstof, abortus, asiel,
energietransitie); de rest ("overig plenair", verreweg de meeste punten) is
ongelabeld plenair/commissiedebat-materiaal. Bovenop de punten ligt een
5-laagse clusterhiërarchie (HDBSCAN), van 7 brede domeinen tot 683 fijne
sub-onderwerpen, elk met een automatisch gegenereerde naam.

## Bestanden in dit pakket

- **`screenshots/preview.png`** -- eerste ruwe preview
  (`scripts/render_design_preview.py`, een snel matplotlib-scriptje, GEEN
  printkwaliteit-renderer): puntenwolk gekleurd per onderwerp
  (semi-transparant, zodat dichtheid zichtbaar wordt), met daaroverheen alle
  5 clusterniveaus als contourlijnen (dikker = grover niveau, dunner =
  dieper niveau -- de gekozen manier om de hiërarchie in één statisch beeld
  te tonen zonder interactief te kunnen zoomen). Nog zonder clusternamen.
- **`screenshots/qgis-sketch.png`** -- een tweede, verder uitgewerkte
  verkenning in QGIS (projectbestand `a0-umap.qgz` + stijlbestanden
  `clusters.qml`/`points.qml` in deze map, zie `qgis-project-notes.md` voor
  details/hoe te openen): clusters gekleurd per ouder-cluster (`parent_id`,
  elke clusterfamilie een eigen kleur) i.p.v. per niveau-dikte, punten als
  kleine zwarte stippen i.p.v. per-onderwerp-kleur, MET labels aan. Let op:
  de getoonde namen ("Schors", "Apel", "Scale", ...) zijn nog de oude,
  rommelige TF-IDF-namen van vóór de labeling-fix -- puur relevant voor de
  VORM/stijl van deze schets, niet voor de getoonde tekst zelf.
- **`styling-tokens.md`** -- dezelfde bestaande kleur-/typografie-tokens als
  in eerdere designpakketten (site-breed "Ink & Rust"-palet).

Beide screenshots zijn twee losse verkenningen van dezelfde data, geen van
beide een vastgelegde richting -- vandaar deze cyclus.

## Vraag aan de designer

Geen eindontwerp nodig -- we zoeken sturing op:
1. **Kleur**: per-onderwerp-kleur (zoals in `preview.png`) of per-cluster-
   groep (zoals in de QGIS-schets)? Of een combinatie?
2. **Dichtheid/leesbaarheid**: bij dit puntenaantal (135k) overheerst de
   grijze "overig plenair"-massa de 4 gekleurde onderwerpen makkelijk --
   ideeën om dat in balans te brengen (bv. de vier onderwerpen prominenter,
   het grijze deel dunner/donkerder) zijn welkom.
3. **Hiërarchie-weergave**: is lijndikte per niveau (deze preview) leesbaar
   genoeg op A0-schaal, of is een ander idee (kleur, transparantie,
   selectieve labeling per niveau) beter?
4. **Typografie/branding**: hoe de titel, legenda en bronvermelding een
   plek geven die past bij het "Ink & Rust"-palet (zie `styling-tokens.md`).

## Status

Clusterbenamingen (LLM-gegenereerd, 1-2 woorden per cluster) staan op het
moment van dit pakket nog te verversen op de achtergrond -- deze preview
toont dus voorlopig nog geen labels/namen, puur vorm en kleur.
