"""
Validatieproef voor issue #270 (wekelijks breed scannen via embeddings):
kan een "zoekcontour" in de bge-m3-ruimte uit de al topic-gelabelde
spreekbeurten per beurt aanwijzen welke beurten over een topic gaan, ook als
het topic niet in de titel van het debat staat?

Eenheid is de spreekbeurt, niet het debat. Een debat over alles (de Algemene
Politieke Beschouwingen) bevat per beurt een ander onderwerp.

Contour per topic ("contrast"): centroid van de positieve seeds min het
gemiddelde van alle beurten. Zonder die correctie scoren korte, interactieve
debatbeurten bij elk topic hoog (debatstijl i.p.v. onderwerp). Ter
vergelijking ook een logistische classifier (seeds tegen beurten zonder
argument, andere topics en een steekproef beurten zonder topic).

Per-beurt-label, zonder handwerk: de LLM-extractie heeft per beurt uit een
topic-debat al een argument opgeleverd (positief) of niet (negatief). De
test is een hold-out: een vijfde van de activiteiten wordt niet gebruikt
voor seeds of training, zodat beurten uit hetzelfde debat niet aan beide
kanten zitten. De labels komen alleen uit topic-debatten, dus de test meet
relevantie binnen zulke debatten; de Algemene Beschouwingen zijn de
kwalitatieve controle daarbuiten (steekproef met de hand beoordeeld voor
abortus, zie het issue).

De drempel per topic is de laagste score waarbij de precision op de
hold-out-beurten MIN_PRECISION haalt.

Niet geintegreerd in de pipeline. Leest data/embeddings/ (make embed) en de
database; schrijft alleen een markdown-rapport.

Gebruik:
    uv run python -m scripts.experiment_topic_contour
    uv run python -m scripts.experiment_topic_contour --show 15 --show-year 2026
"""

import argparse
import logging
import re
import zlib
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from pipeline.db import db
from pipeline.embed.documents import CACHE_DIR, MODEL, load_embedding_cache
from pipeline.paths import REPO_ROOT

logger = logging.getLogger(__name__)

OUTPUT_PATH = REPO_ROOT / "docs" / "poc" / "topic-contour" / "rapport.md"
RANDOM_SEED = 20261010
TEST_FRACTION_DENOMINATOR = 5  # een vijfde van de activiteiten als hold-out
MIN_PRECISION = 0.8
MIN_SELECTED_FOR_THRESHOLD = 20
APB_PREFIX = "Algemene Politieke Beschouwingen"


def load_matrix(label):
    cache = load_embedding_cache(CACHE_DIR / f"{MODEL}_plenair-{label}")
    if not cache:
        raise SystemExit(f"geen embeddings-cache voor label {label!r}; draai eerst make embed")
    ids = np.fromiter(cache.keys(), dtype=np.int64, count=len(cache))
    matrix = np.stack([cache[int(i)] for i in ids]).astype(np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix /= np.where(norms == 0, 1, norms)
    return ids, matrix


def load_document_meta(conn):
    rows = conn.execute(
        """
        SELECT d.id, d.topic_id, d.activiteit_nummer, d.title,
               substr(d.activiteit_aanvangstijd, 1, 10) AS day, d.is_voorzitter_turn, d.content,
               d.extraction_attempted_at IS NOT NULL AS extracted,
               EXISTS (SELECT 1 FROM arguments a WHERE a.document_id = d.id) AS has_argument
        FROM documents d
        """
    ).fetchall()
    return {r["id"]: r for r in rows}


def pick_test_activities(meta):
    """Per topic een vijfde van de activiteiten (op een vaste hash-volgorde)
    als hold-out, zodat ook topics met weinig activiteiten testbeurten
    houden. Activiteiten zonder topic: hash % 5 == 0."""
    by_topic = defaultdict(set)
    for row in meta.values():
        if row["activiteit_nummer"] and row["topic_id"] is not None:
            by_topic[row["topic_id"]].add(row["activiteit_nummer"])
    test = set()
    for activities in by_topic.values():
        ordered = sorted(activities, key=lambda a: zlib.crc32(a.encode()))
        test.update(ordered[: max(1, round(len(ordered) / TEST_FRACTION_DENOMINATOR))])
    return test


def threshold_for_precision(scores, labels, min_precision):
    """Laagste score waarbij het geselecteerde deel (score >= drempel)
    min_precision haalt, met minstens MIN_SELECTED_FOR_THRESHOLD beurten."""
    order = np.argsort(-scores)
    hits = np.cumsum(labels[order])
    precision = hits / np.arange(1, len(order) + 1)
    ok = np.flatnonzero((precision >= min_precision) & (np.arange(1, len(order) + 1) >= MIN_SELECTED_FOR_THRESHOLD))
    if len(ok) == 0:
        return None
    return float(scores[order[ok[-1]]])


def split_speaker(text):
    m = re.match(r"^([^:]{3,80}):\s+(.*)$", text, re.S)
    return (m.group(1), m.group(2)) if m else ("", text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", default="full", help="label van de embeddings-cache (default: full)")
    parser.add_argument("--show", type=int, default=8, help="aantal topbeurten per topic in het APB-voorbeeld")
    parser.add_argument("--show-year", default="2026", help="APB-jaar waarvan de topbeurten getoond worden")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    rng = np.random.default_rng(RANDOM_SEED)

    conn = db.connect()
    try:
        topics = {r["id"]: r["slug"] for r in conn.execute("SELECT id, slug FROM topics ORDER BY slug")}
        meta = load_document_meta(conn)
    finally:
        conn.close()  # niet openhouden: andere stappen schakelen de journal_mode

    logger.info("embeddings laden ...")
    ids, matrix = load_matrix(args.label)
    keep = np.array([int(i) in meta and not meta[int(i)]["is_voorzitter_turn"] for i in ids])
    ids, matrix = ids[keep], matrix[keep]
    n = len(ids)
    topic_of = np.array([meta[int(i)]["topic_id"] or 0 for i in ids], dtype=np.int64)
    extracted = np.array([bool(meta[int(i)]["extracted"]) for i in ids])
    has_arg = np.array([bool(meta[int(i)]["has_argument"]) for i in ids])
    test_activities = pick_test_activities(meta)
    in_test = np.array([meta[int(i)]["activiteit_nummer"] in test_activities for i in ids])
    logger.info("%d beurten, %d met topic, %d geextraheerd", n, int((topic_of != 0).sum()), int(extracted.sum()))

    global_mean = matrix[rng.choice(n, size=min(100_000, n), replace=False)].mean(axis=0)
    null_rows = np.flatnonzero((topic_of == 0) & ~in_test)
    null_sample = rng.choice(null_rows, size=min(60_000, len(null_rows)), replace=False)

    apb_rows = np.array([r for r, i in enumerate(ids) if (meta[int(i)]["title"] or "").startswith(APB_PREFIX)])
    apb_days = np.array([meta[int(ids[r])]["day"] for r in apb_rows])
    lines = ["# Topic-contour: validatie per spreekbeurt (#270)", "",
             f"Embeddings `{args.label}`, {n} beurten (voorzitterbeurten uitgesloten). Opzet en beperkingen: "
             "`scripts/experiment_topic_contour.py`.", "",
             "## Hold-out op extractielabels", "",
             "Test = beurten uit topic-debatten die al door de extractie zijn gehaald, uit activiteiten die niet "
             "voor seeds of training zijn gebruikt. Positief = de beurt leverde een argument op. "
             f"Drempel = laagste score met precision >= {MIN_PRECISION:.0%} op de test.", "",
             "| Topic | Methode | Test (pos / neg) | AUC | AP | Drempel | Recall bij drempel | Beurten APB boven drempel |",
             "|---|---|---|---|---|---|---|---|"]
    apb_blocks = []

    for topic_id, slug in topics.items():
        topic_rows = topic_of == topic_id
        pos_train = np.flatnonzero(topic_rows & extracted & has_arg & ~in_test)
        neg_topic_train = np.flatnonzero(topic_rows & extracted & ~has_arg & ~in_test)
        test = np.flatnonzero(topic_rows & extracted & in_test)
        if len(pos_train) < 50 or len(test) < 40 or has_arg[test].sum() < 10:
            lines.append(f"| {slug} | (te weinig data: {len(pos_train)} seeds, {len(test)} testbeurten) | | | | | | |")
            continue
        y = has_arg[test].astype(int)

        centroid = matrix[pos_train].mean(axis=0)
        contrast = centroid - global_mean
        contrast /= np.linalg.norm(contrast)

        other = np.flatnonzero((topic_of != topic_id) & (topic_of != 0) & ~in_test)
        other = rng.choice(other, size=min(60_000, len(other)), replace=False)
        neg_rows = np.concatenate([neg_topic_train, other, null_sample])
        train_pos = pos_train if len(pos_train) <= 40_000 else rng.choice(pos_train, 40_000, replace=False)
        clf = LogisticRegression(max_iter=300, class_weight="balanced")
        clf.fit(np.vstack([matrix[train_pos], matrix[neg_rows]]),
                np.concatenate([np.ones(len(train_pos)), np.zeros(len(neg_rows))]))

        methods = {"contrast": lambda m: m @ contrast, "classifier": lambda m: clf.predict_proba(m)[:, 1]}
        for name, score_fn in methods.items():
            test_scores = score_fn(matrix[test])
            thr = threshold_for_precision(test_scores, y, MIN_PRECISION)
            auc, ap = roc_auc_score(y, test_scores), average_precision_score(y, test_scores)
            if thr is None:
                lines.append(f"| {slug} | {name} | {int(y.sum())} / {int((1 - y).sum())} | {auc:.3f} | {ap:.3f} | "
                             f"precision {MIN_PRECISION:.0%} niet haalbaar | | |")
                continue
            recall = float((test_scores[y == 1] >= thr).mean())
            apb_scores = score_fn(matrix[apb_rows])
            above = apb_scores >= thr
            lines.append(f"| {slug} | {name} | {int(y.sum())} / {int((1 - y).sum())} | {auc:.3f} | {ap:.3f} | "
                         f"{thr:.3f} | {recall:.0%} | {int(above.sum())} van {len(apb_rows)} |")
            if name == "contrast":
                year_mask = np.array([d.startswith(args.show_year) for d in apb_days])
                idx = np.flatnonzero(year_mask)
                top = idx[np.argsort(-apb_scores[idx])[: args.show]]
                apb_blocks.append((slug, thr, [(float(apb_scores[t]), int(ids[apb_rows[t]])) for t in top]))
        logger.info("%s klaar (%d seeds, %d testbeurten)", slug, len(pos_train), len(test))

    lines += ["", f"## Algemene Politieke Beschouwingen {args.show_year}: topbeurten per topic (contrast)", "",
              "Score met de drempel van het topic ernaast. Boven de drempel is de beurt een kandidaat."]
    for slug, thr, top in apb_blocks:
        lines += ["", f"### {slug} (drempel {thr:.3f})", ""]
        for score, doc_id in top:
            speaker, text = split_speaker(re.sub(r"\s+", " ", meta[doc_id]["content"] or ""))
            mark = "boven" if score >= thr else "onder"
            lines.append(f"- {score:.3f} ({mark}) {speaker}: {text[:220]}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n")
    logger.info("rapport geschreven naar %s", args.output)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
