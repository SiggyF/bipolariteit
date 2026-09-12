# Hiërarchische clustering van plenaire spreekbeurten

Vervolg op [issue #181](https://github.com/SiggyF/bipolariteit/issues/181) (clusterpositionering & clusterlabels). Beschrijft de aanpak in
[notebooks/explore_plenary_umap_clusters.py](../notebooks/explore_plenary_umap_clusters.py):
een experimenteerscript op een steekproef spreekbeurten, los van de productie-pipeline
(`pipeline/plenary_map/cluster.py`, die de volle ~99k-dataset draait en naar
`data/export/plenair-map*.json` schrijft).

## Het probleem: vaste HDBSCAN-drempels werken niet

HDBSCAN clustert op dichtheid met een `min_cluster_size`-drempel. Met de standaard
`cluster_selection_method="eom"` (excess-of-mass) kiest HDBSCAN het meest *stabiele*
niveau uit zijn hiërarchie -- en dat bleek op deze data, op elke geprobeerde schaal, bijna
altijd "de hele kaart":

- Steekproef van 3.000 spreekbeurten, `min_cluster_size=15`: **2 clusters**, één met >95%
  van de punten.
- Volledige periode, ~39.630 spreekbeurten, `min_cluster_size=15`: 224 clusters zonder
  collapse, maar veel te fijnmazig (224 LLM-naamgevingscalls) voor bruikbare labels.
- Diezelfde 39.630 punten met een coarse/fine-tweedeling (`200`/`15`, zoals de volle
  pipeline gebruikt): coarse collapst zelf ook weer -- 3 domeinen, één met 94% van de
  punten.

Geen van deze vaste drempels geeft dus een handzaam *en* betekenisvol aantal clusters.

## De aanpak: de condensed tree top-down aflopen

In plaats van één vaste drempel wandelt het script de volledige HDBSCAN-hiërarchie (de
*condensed tree*, opgebouwd met een lage drempel `HDBSCAN_MIN_CLUSTER_SIZE=15`) zelf af,
top-down, via `build_cluster_tree()`:

1. Start bij de hoofdtak (alle punten samen).
2. Bij elke splitsing: als de kleinste van de twee subtakken groot genoeg is
   (`>= CLUSTER_MIN_SIZE_TO_NAME`), krijgt die subtak een eigen naam -- én wordt zelf
   weer op dezelfde manier verder doorzocht op interne sub-splitsingen. Zo'n al
   afgesplitste kleinere categorie kan dus zelf later in twee (of meer) sub-categorieën
   uiteenvallen (live gezien: een tak van 302 spreekbeurten bleek zelf in twee groepen
   van 144 en 147 te splitsen -- beide kregen een eigen naam).
3. Is een subtak te klein om apart te noemen, dan versmelt hij met de rest (geen aparte
   naam, geen verloren punten).
4. Zodra de resterende hoofdtak zelf geen splitsing meer heeft waarvan de kleinste kant
   groot genoeg is, wordt wat er dan nog over is (incl. alle versmolten te-kleine
   subtakken) zelf ook één laatste cluster.

Dit geeft een échte, meerlagige hiërarchie (elk cluster heeft een `diepte`: hoeveel
splitsingen diep het van de hoofdtak af zit) in plaats van een platte lijst, zonder dat er
een vast aantal niveaus hoeft te worden voorgeschreven.

## `CLUSTER_MIN_SIZE_TO_NAME`: hoeveel clusters levert dit op?

Live gemeten op de volle periode (~39.630 spreekbeurten):

| `CLUSTER_MIN_SIZE_TO_NAME` | aantal clusters |
|---:|---:|
| 100 | 84 |
| 200 | 48 |
| 300 | 31 |
| 500 | 18 |

Lager = fijnmaziger (meer clusters, dus meer LLM-naamgevingscalls); hoger = grover.
Huidige default: `200` (~48 clusters). Ter indicatie: er zijn een tiental ministeries,
elk met een aantal grote onderwerpen -- 48 clusters is een redelijk startpunt, maar
waarschijnlijk is nog een fijnere drempel nodig om dat aantal echt te dekken (zie
[issue #181](https://github.com/SiggyF/bipolariteit/issues/181)).

## Kosten: LLM-naamgeving

Elk genoemde cluster krijgt een LLM-gegenereerde naam + duiding (stap 5b in het script),
op basis van TF-IDF-trefwoorden + een paar representatieve spreekbeurten. Live gemeten
tegen LM Studio: een realistische cluster-naming-prompt (8 voorbeeldfragmenten +
debattitels, ~600 prompt-tokens) kost **~7 seconden**. Bij 48 clusters is dat sequentieel
~5-6 minuten. Bundelen van meerdere clusters in één LLM-call is overwogen maar niet
gedaan: de tijd zit vooral in tokens verwerken/genereren (niet in HTTP-overhead), dus dat
scheelt weinig en maakt het parsen van het antwoord fragieler.

## Draaien

```
uv run python notebooks/explore_plenary_umap_clusters.py
```

Schrijft twee PNG's (geen `plt.show()` -- dat toont niets buiten een notebook, en Claude
Code kan geen Jupyter-notebooks in deze VS Code-omgeving draaien, zie project-memory):

- `notebooks/explore_plenary_umap_clusters.png` -- de UMAP-clusterkaart.
- `notebooks/explore_plenary_umap_clusters_condensed_tree.png` -- de condensed tree van
  de clusterer (kan bij veel clusters een matplotlib-bug raken bij het tekenen; dan wordt
  die stap overgeslagen, de rest van de run gaat door).

CONFIG-constanten bovenin het script (`SAMPLE_SIZE`, `HDBSCAN_MIN_CLUSTER_SIZE`,
`CLUSTER_MIN_SIZE_TO_NAME`, ...) zijn de knoppen om aan te draaien.

## Bekende beperkingen / vervolg

- Geen koppeling met Kamerstukdossiers (TK's eigen onderwerpcodes, bv. dossier 36847 =
  Borssele) als vergelijkingslaag -- zie [issue #183](https://github.com/SiggyF/bipolariteit/issues/183).
- De condensed-tree-plot crasht soms bij veel clusters (matplotlib `ValueError` bij het
  tekenen van te veel select-cluster-markers); staat in een `try/except` zodat de rest van
  de run niet stopt.
- `CLUSTER_MIN_SIZE_TO_NAME=200` is een eerste, nog niet definitief gekalibreerde keuze
  (zie ministeries-opmerking hierboven) -- nog niet vervolgd.
