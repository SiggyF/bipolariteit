# Architectuuradvies & Aandachtspunten: Samenvoegen Clustering-verbeteringen (#281 / #186)

Dit document bevat de architectuur-aandachtspunten, ontwerpprincipes en trade-offs naar aanleiding van de vragen in `request-for-architect-input.md` (issue [#281](https://github.com/SiggyF/bipolariteit/issues/281) ter afronding van [#186](https://github.com/SiggyF/bipolariteit/issues/186)).

---

## 1. Single Source of Truth vs. Pijplijn-divergentie
* **Vraag:** Wordt `build_multilevel_clusters` / `label_multilevel_clusters` de nieuwe standaard voor beide paden?
* **Aandachtspunt:** Twee parallelle clustering-implementaties (`build_hierarchical` in productie vs. `build_multilevel` in het posterpad) veroorzaken semantische divergentie tussen de webkaart, de printposter en de argumentenboom.
* **Architectuurprincipe:** *Één centrale clustering-pijplijn.* `build_multilevel_clusters` wordt de enige bron van waarheid.
* **Afweging:** De oude coarse-methode liet bij grotere drempels een gigantische hoofdtak ("Schors", 59% van de punten) als cluster staan. `build_multilevel_clusters` lost dit op via `partition_exhaustive`. Door `level_sizes` als parameter te voeden, bedient dezelfde functie zowel $N=2$ (de huidige webkaart) als $N>2$ (print en toekomstige vector-tegels). De oude functies kunnen worden uitgefaseerd; `notebooks/explore_plenary_umap_clusters.py` wordt omgezet naar `build_multilevel_clusters`.

---

## 2. Semantische Ruis vs. Dataderving (Oplossing voor #186 punt 2)
* **Aandachtspunt:** Dominantie-afwijzing (`dominance_ratio=4.0`) degradeert de amorfe 59%-hoofdtak naar ruis (`-1`).
* **Architectuurprincipe:** *Strikte scheiding tussen thematisch zwaartepunt en databeschikbaarheid.*
* **Afweging:** Ruis betekent niet dat data verdwijnt voor de burger. De punten blijven 100% aanwezig in de puntenwolk, doorzoekbaar en aanklikbaar. Ruis markeert slechts de afwezigheid van een specifiek inhoudelijk beleidsthema (zoals procedurele debatten of de regeling van werkzaamheden). We accepteren het verlies van een misleidend macro-cluster om scherpe, betekenisvolle subthema's over te houden.

---

## 3. "Fat Pipeline, Thin Client" voor Topologie (Oplossing voor #186 punt 4)
* **Vraag:** Hoe landen `contained_by_sibling` en `redundant_with_parent` concreet in interactieve hull-rendering?
* **Aandachtspunt:** Convex hulls zijn wiskundig goedkoop maar tonen visuele overlap bij concave debatten. Dynamische concave hulls (alpha-shapes) in JavaScript op de client draaien leidt tot framedrops en batterijdrain op mobiele apparaten (zie benchmarks in issue #186).
* **Architectuurprincipe:** *Complexe meetkunde offline berekenen; eenvoudige O(1) filterregels in de client.*
* **Afweging:** De Python-pijplijn berekent topologische eigenschappen vooraf en voegt declaratieve vlaggen toe:
  - `redundant_with_parent`: kind-cluster deelt $\ge 80\%$ geometrische IoU met de ouder (voegt ruimtelijk niets toe).
  - `contained_by_sibling`: kleiner cluster wordt ruimtelijk omsloten door de convex hull van een disjunct groter buurcluster (convex-hull renderartefact).
  De browser past een eenvoudige filterregel toe: teken de contour niet als een vlag actief is (analoog aan `render_design_preview.py`). Geen runtime-rekenkracht nodig, wel direct visueel gescheiden hulls.

---

## 4. Ontkoppeling van Datacontract en Render-engine (#259)
* **Vraag:** Kan restgroep/overlap-mitigatie landen in `PlenairMap.vue` los van de bredere #259-vraag?
* **Aandachtspunt:** Moet het oplossen van productiefouten in #186 wachten op de transitie naar vector-tegels (`TiledPlenairMap.vue` / #259)?
* **Architectuurprincipe:** *Data-export als stabiele laag; renderers als inwisselbare consumenten.*
* **Afweging:** De verbeteringen horen primair thuis in de data-export (`plenair-map-clusters.json`). Zowel de huidige productiekaart (`PlenairMap.vue`) als het experimentele alternatief (`TiledPlenairMap.vue`) zijn consumenten van ditzelfde bestand. Door de clustering direct in de export te verbeteren en toe te passen in `PlenairMap.vue`, wordt #186 per direct opgelost in productie. Zodra #259 volwassen is, profiteert die automatisch van dezelfde data.

---

## 5. Contractevolutie en Schaalbaarheid (Payload Limits)
* **Vraag:** Vergt dit een nieuw contract voor de exportbestanden?
* **Aandachtspunt:** Cloudflare Workers kent een harde limiet van 25 MiB voor statische assets; de export mag door extra niveaus en metadata niet opblazen.
* **Architectuurprincipe:** *Canonieke uitbreiding zonder data-duplicatie.*
* **Afweging:** We behouden compacte index-tabellen in `plenair-map.json`. In `plenair-map-clusters.json` blijven `coarse` en `fine` als directe top-level sleutels beschikbaar voor backward compatibility, verrijkt met de booleans, terwijl een geneste `levels`-array $N$-laagse visualisaties faciliteert:
  ```json
  {
    "levels": [ [/* niveau 0 */], [/* niveau 1 */] ],
    "coarse": [/* niveau 0 clusters met vlaggen */],
    "fine": [/* niveau 1 clusters met vlaggen */]
  }
  ```

---

## 6. Systeemboundary: Kaart vs. Argumentenboom (Synergie zonder Koppeling)
* **Aandachtspunt:** Hoe beïnvloedt deze clustering de argumentenboom (SOTA-upgrade #175 / #254)?
* **Architectuurprincipe:** *Descriptief (kaart) vs. Dialectisch (boom).*
* **Afweging:**
  - **De kaart** modelleert statistische correlatie in taal (`bge-m3`), maar begrijpt geen logische tegenspraak of drogredenen.
  - **De boom** modelleert pragma-dialectische relaties (AIF: support/conflict).
  - **Koppeling:** Er is géén interactieve runtime UI-koppeling. De overdracht is puur asynchrone data-invoer: de clustering signaleert "witte vlekken" (dichte subthema's op de kaart die ontbreken in de boom) als gerichte input voor de extractie-pijplijn.
