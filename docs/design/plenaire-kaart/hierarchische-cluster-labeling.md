# Gids: Hiërarchische Cluster Labeling op Basis van bge-m3 Embeddings

Dit document beschrijft een robuuste architectuur om betekenisvolle, contextbewuste labels toe te kennen aan hiërarchische vectorclusters (van brede hoofdcategorieën tot specifieke subclusters) op basis van `bge-m3` (1024-dimensionale vectoren).

---

## 1. Het Kernprobleem

Een cluster-centerpoint (centroid) is een mathematisch gemiddelde van 1024 floating-point getallen. Een encoder-only model zoals `bge-m3` kan niet omgekeerd worden om direct tekst uit een vector te genereren.

Bij **hiërarchische clusters** ontstaat een extra uitdaging: **granulariteitsverwarring**.
* Zonder hiërarchische context krijgen zowel ruime bovenliggende clusters als smalle subclusters vaak hetzelfde generieke label (bijv. allebei *"Facturen"*).
* Een goed labelsysteem forceert **abstractie** aan de top en **differentiatie** in de diepte.

```
Niveau 1 (Ruim):   [ Financiële Administratie & Betalingen ]
                           │
             ┌─────────────┴─────────────┐
Niveau 2:    ▼                           ▼
      [ Facturatie & Facturen ]    [ Incassoprocedures ]
             │
             ├─► [ Onbekende betalingskenmerken ]  (Niveau 3, Smal)
             └─► [ Aanvragen uitstel betaling ]    (Niveau 3, Smal)
```

---

## 2. Aanbevolen Architectuur: Top-Down Conditioned Medoids + LLM

De meest betrouwbare en interpreteerbare methode combineert:
1. **Centroid-gebaseerde Medoid selectie:** Bepaal welke werkelijke documenten het dichtst bij het wiskundige middelpunt van het cluster liggen.
2. **Top-Down Conditionering:** Gebruik het label van het bovenliggende cluster als contextrestrictie voor het onderliggende cluster.

### Stap 1: Mathematische Representatie (Centroid & Medoids)

Laat een cluster $C$ bestaan uit $N$ genormaliseerde vectoren $\vec{v}_1, \vec{v}_2, \dots, \vec{v}_N \in \mathbb{R}^{1024}$.

1. Bereken de genormaliseerde centroid $\vec{c}$:
   $$\vec{c} = \frac{\sum_{i=1}^N \vec{v}_i}{\left\| \sum_{i=1}^N \vec{v}_i \right\|_2}$$

2. Bereken de cosine similarity van alle documenten in het cluster ten opzichte van $\vec{c}$:
   $$s_i = \vec{v}_i \cdot \vec{c}$$

3. Rangschik aflopend en selecteer de top-$k$ documenten (bijv. $k = 3$ tot $5$). Dit zijn de **medoids**: de meest representatieve, ruisvrije voorbeelden van het cluster.

---

### Stap 2: Hiërarchische Promptstrategie

Doorloop de hiërarchie van boven naar beneden (breadth-first of depth-first):

#### A. Voor Ruime / Hoogste Categorieën (Niveau 1)
Het doel hier is **synthese en abstractie**.

* **Prompt:**
  ```text
  Je bent een data-architect gespecialiseerd in taxonomieën.
  Hier zijn 4 representatieve documenten die het middelpunt vormen van een brede gegevensgroep:

  - [Document 1]
  - [Document 2]
  - [Document 3]
  - [Document 4]

  Geef een beknopt, overkoepelend categorielabel (1 tot maximaal 3 woorden) dat het algemene domein dekt.
  Antwoord uitsluitend met het label, zonder toelichting.
  ```

#### B. Voor Smalle / Diepere Subclusters (Niveau 2+)
Het doel hier is **onderscheidend vermogen (differentiatie)** ten opzichte van de ouder en zusternodes.

* **Prompt:**
  ```text
  Je verfijnt een bestaande taxonomie.
  Bovenliggende categorie: "{parent_label}"

  Hieronder staan 4 representatieve documenten uit een specifiek subcluster binnen deze categorie:
  - [Document 1]
  - [Document 2]
  - [Document 3]
  - [Document 4]

  Geef een specifiek sublabel (maximaal 4 woorden) dat beschrijft wat DIT specifieke cluster uniek maakt binnen "{parent_label}".
  - Herhaal niet simpelweg de bovenliggende term.
  - Focus op het specifieke onderwerp, actie of probleem.
  Antwoord uitsluitend met het sublabel.
  ```

---

## 3. Alternatief Zonder LLM: Hiërarchische c-TF-IDF

Indien kosten, latentie of privacy het gebruik van een extern LLM verhinderen:

1. **Root-niveau:** Bereken TF-IDF over de samengevoegde teksten van alle hoofdclusters. Termen met een hoge IDF scheiden de hoofddomeinen.
2. **Subcluster-niveau:** Bereken TF-IDF **uitsluitend binnen de scope van het bovenliggende cluster** (alleen de siblings vergelijken). 
   * Woorden die kenmerkend zijn voor het hoofddomein (bijv. *"factuur"*) komen in alle subclusters voor en krijgen automatisch een IDF van $\approx 0$.
   * Alleen termen die specifiek zijn voor het subcluster (bijv. *"storno"*, *"incasso"*, *"herinnering"*) komen bovendrijven als labeltermen.

---

## 4. Referentie-implementatie (Python)

```python
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

@dataclass
class ClusterNode:
    node_id: str
    indices: List[int]                # Indexen van documenten die in dit cluster vallen
    children: List['ClusterNode']
    parent_label: Optional[str] = None
    label: Optional[str] = None

def compute_normalized_centroid(vectors: np.ndarray) -> np.ndarray:
    """Berekent de L2-genormaliseerde centroid van een set vectoren."""
    centroid = np.mean(vectors, axis=0)
    norm = np.linalg.norm(centroid)
    return centroid / norm if norm > 0 else centroid

def extract_medoids(
    centroid: np.ndarray, 
    vectors: np.ndarray, 
    texts: List[str], 
    top_k: int = 4
) -> List[str]:
    """Vindt de documenten die semantisch het dichtst bij het centerpoint liggen."""
    # Cosine similarity via inproduct (ervan uitgaande dat vectoren L2-genormaliseerd zijn)
    similarities = np.dot(vectors, centroid)
    top_indices = np.argsort(similarities)[::-1][:top_k]
    return [texts[idx] for idx in top_indices]

def generate_label(prompt: str) -> str:
    """Placeholder voor je favoriete LLM-aanroep (bijv. Ollama, OpenAI, Claude)."""
    # response = client.chat.completions.create(...)
    # return response.choices[0].message.content.strip()
    return "Dummy Label"

def label_cluster_tree(
    node: ClusterNode, 
    all_vectors: np.ndarray, 
    all_texts: List[str], 
    depth: int = 1
):
    """Doorloopt de hiërarchie recursief en wijst contextbewuste labels toe."""
    sub_vectors = all_vectors[node.indices]
    sub_texts = [all_texts[i] for i in node.indices]
    
    # 1. Bepaal centroid en dichtstbijzijnde teksten
    centroid = compute_normalized_centroid(sub_vectors)
    medoids = extract_medoids(centroid, sub_vectors, sub_texts, top_k=4)
    medoids_bullet = "\n".join(f"- {txt[:200]}" for txt in medoids)

    # 2. Stel prompt op afhankelijk van hiërarchische diepte
    if depth == 1 or node.parent_label is None:
        prompt = (
            "Geef een breed, overkoepelend categorielabel (1-3 woorden) "
            f"voor een cluster met deze centrale teksten:\n{medoids_bullet}"
        )
    else:
        prompt = (
            f"Bovenliggende categorie: \"{node.parent_label}\"\n"
            "Geef een specifiek sublabel (max 4 woorden) dat aangeeft waarin dit "
            f"subcluster zich onderscheidt binnen \"{node.parent_label}\":\n{medoids_bullet}"
        )
        
    node.label = generate_label(prompt)

    # 3. Verwerk subclusters (recursie)
    for child in node.children:
        child.parent_label = node.label
        label_cluster_tree(child, all_vectors, all_texts, depth=depth + 1)
```

---

## 5. Best Practices & Optimalisaties

1. **Normaliseer altijd de vectoren:** `bge-m3` levert standaard genormaliseerde vectoren op. Telkens wanneer je een gemiddelde berekent, moet je de resulterende vector opnieuw L2-normaliseren (`v / ||v||`).
2. **Knip te lange teksten af:** Voor de prompt zijn alleen de eerste 150-250 tekens per document meestal al voldoende. Dit bespaart tokens en voorkomt contextvervuiling.
3. **Filter clusters met te weinig data:** Als een cluster minder dan 3 documenten heeft, is de centroid statistisch onbetrouwbaar. Voeg deze samen met het zusterniveau of markeer als `"Overig"`.
4. **Vergelijk siblings voor validatie:** Laat in een optionele tweede pas de LLM alle sublabels onder één ouder zien om eventuele synoniemen of dubbelingen glad te strijken.