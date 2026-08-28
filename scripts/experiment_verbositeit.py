"""
Verkenning van "langdradigheid" vs "compactheid" per spreker (issue #155):
zegt iemand veel in weinig tekst, of juist veel tekst voor weinig
onderbouwing? Puur op bestaande data (documents/arguments/claims), geen
nieuwe LLM-extractie.

Twee soorten maten, per actor geaggregeerd:

- Inhoudelijke dichtheid (documents + arguments + claims):
  argumenten per 1000 tekens sprekerbeurt, claims per argument,
  gemiddelde quote_text-lengte, gemiddelde sprekerbeurt-lengte.
- Leesbaarheid/verbositeit van de brontekst zelf (documents.content):
  gemiddelde zinslengte, Flesch-Douma-leesindex, type-token ratio, LIX.
  Lettergreeptelling is een vocaal-groepen-heuristiek (geen echte NL-
  hyphenator), dus Flesch-Douma en LIX zijn indicatief, geen exacte score.
- Tokenizer-maat (o200k_base via tiktoken, geen LLM-forward-pass): tokens
  per zin en tokens per teken, als taalmodel-bewuste informatiedichtheid --
  minder tokens per teken = voorspelbaardere/eenvoudigere formuleringen.

Nog niet geintegreerd in de pipeline of export -- eerst los bekijken of dit
iets zinnigs oplevert (zie issue #155), bv. voor topic asiel.

Gebruik:
    uv run python scripts/experiment_verbositeit.py --topic asiel
    uv run python scripts/experiment_verbositeit.py --alle-topics --min-documenten 3
"""

import argparse
import re
from collections import defaultdict

import tiktoken

from pipeline.db import db

_WOORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_ZIN_SPLIT_RE = re.compile(r"[.!?]+(?:\s+|$)")
_VOCAAL_GROEP_RE = re.compile(r"[aeiouyàáâäèéêëìíîïòóôöùúûü]+", re.IGNORECASE)
_ENCODING = tiktoken.get_encoding("o200k_base")


def _zinnen(tekst):
    kandidaten = [z.strip() for z in _ZIN_SPLIT_RE.split(tekst)]
    return [z for z in kandidaten if _WOORD_RE.search(z)]


def _lettergrepen(woord):
    # Vocaal-groepen-heuristiek: elke aaneengesloten reeks klinkers telt als
    # één lettergreep. Geen echte NL-hyphenator, maar voldoende voor een
    # grove, snelle indicatie zonder externe dependency.
    return max(1, len(_VOCAAL_GROEP_RE.findall(woord)))


def tekststatistieken(tekst):
    woorden = _WOORD_RE.findall(tekst)
    zinnen = _zinnen(tekst)
    n_woorden = len(woorden)
    n_zinnen = len(zinnen) or 1

    lettergrepen = sum(_lettergrepen(w) for w in woorden)
    lange_woorden = sum(1 for w in woorden if len(w) > 6)
    unieke_woorden = {w.lower() for w in woorden}

    gem_zinslengte = n_woorden / n_zinnen
    gem_lettergrepen_per_woord = lettergrepen / n_woorden if n_woorden else 0.0

    flesch_douma = 206.84 - 0.93 * gem_zinslengte - 77 * gem_lettergrepen_per_woord
    lix = gem_zinslengte + (lange_woorden * 100 / n_woorden if n_woorden else 0.0)
    ttr = len(unieke_woorden) / n_woorden if n_woorden else 0.0
    n_tokens = len(_ENCODING.encode(tekst))

    return {
        "n_woorden": n_woorden,
        "n_zinnen": n_zinnen,
        "gem_zinslengte": gem_zinslengte,
        "flesch_douma": flesch_douma,
        "lix": lix,
        "ttr": ttr,
        "n_tokens": n_tokens,
    }


def fetch_documenten(conn, topic_slug):
    query = """
        SELECT d.id, d.content, d.actor_id
        FROM documents d
        JOIN topics t ON t.id = d.topic_id
        WHERE d.is_voorzitter_turn = 0
          AND d.actor_id IS NOT NULL
          AND d.content IS NOT NULL
          AND length(d.content) > 0
    """
    params = ()
    if topic_slug:
        query += " AND t.slug = ?"
        params = (topic_slug,)
    return conn.execute(query, params).fetchall()


def fetch_argumenten(conn, topic_slug):
    query = """
        SELECT a.id, a.actor_id, length(a.quote_text) AS quote_lengte,
               (SELECT COUNT(*) FROM claims c WHERE c.argument_id = a.id) AS n_claims
        FROM arguments a
        JOIN topics t ON t.id = a.topic_id
        WHERE 1 = 1
    """
    params = ()
    if topic_slug:
        query += " AND t.slug = ?"
        params = (topic_slug,)
    return conn.execute(query, params).fetchall()


def aggregeer_per_actor(conn, topic_slug):
    documenten = fetch_documenten(conn, topic_slug)
    argumenten = fetch_argumenten(conn, topic_slug)

    per_actor = defaultdict(
        lambda: {
            "n_documenten": 0,
            "totaal_tekens": 0,
            "totaal_woorden": 0,
            "totaal_zinnen": 0,
            "totaal_tokens": 0,
            "totaal_lettergrepen_per_woord": 0.0,
            "unieke_woorden": set(),
            "flesch_douma_som": 0.0,
            "lix_som": 0.0,
            "n_argumenten": 0,
            "totaal_quote_lengte": 0,
            "n_claims": 0,
        }
    )

    for doc in documenten:
        stats = tekststatistieken(doc["content"])
        actor = per_actor[doc["actor_id"]]
        actor["n_documenten"] += 1
        actor["totaal_tekens"] += len(doc["content"])
        actor["totaal_woorden"] += stats["n_woorden"]
        actor["totaal_zinnen"] += stats["n_zinnen"]
        actor["totaal_tokens"] += stats["n_tokens"]
        actor["flesch_douma_som"] += stats["flesch_douma"] * stats["n_woorden"]
        actor["lix_som"] += stats["lix"] * stats["n_woorden"]
        actor["unieke_woorden"] |= set(_WOORD_RE.findall(doc["content"].lower()))

    for arg in argumenten:
        actor = per_actor[arg["actor_id"]]
        actor["n_argumenten"] += 1
        actor["totaal_quote_lengte"] += arg["quote_lengte"] or 0
        actor["n_claims"] += arg["n_claims"]

    return per_actor


def actor_namen(conn):
    rows = conn.execute("SELECT id, name, party FROM actors").fetchall()
    return {row["id"]: (row["name"], row["party"]) for row in rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", default="asiel", help="topic-slug (default: asiel)")
    parser.add_argument("--alle-topics", action="store_true", help="negeer --topic, alle topics samen")
    parser.add_argument("--min-documenten", type=int, default=2, help="minimum aantal sprekerbeurten om mee te tellen")
    parser.add_argument(
        "--min-argumenten",
        type=int,
        default=1,
        help="minimum aantal argumenten om mee te tellen (0 = ook sprekers zonder argumenten tonen, bv. nog niet geëxtraheerd of geen relevante content voor dit topic)",
    )
    parser.add_argument("--sorteer", choices=["argumenten_per_1000", "flesch_douma", "claims_per_argument"], default="argumenten_per_1000")
    args = parser.parse_args()

    conn = db.connect()
    topic_slug = None if args.alle_topics else args.topic
    per_actor = aggregeer_per_actor(conn, topic_slug)
    namen = actor_namen(conn)

    rijen = []
    for actor_id, s in per_actor.items():
        if s["n_documenten"] < args.min_documenten or s["n_argumenten"] < args.min_argumenten:
            continue
        naam, partij = namen.get(actor_id, (f"actor {actor_id}", None))
        gem_zinslengte = s["totaal_woorden"] / s["totaal_zinnen"] if s["totaal_zinnen"] else 0.0
        flesch_douma = s["flesch_douma_som"] / s["totaal_woorden"] if s["totaal_woorden"] else 0.0
        lix = s["lix_som"] / s["totaal_woorden"] if s["totaal_woorden"] else 0.0
        ttr = len(s["unieke_woorden"]) / s["totaal_woorden"] if s["totaal_woorden"] else 0.0
        argumenten_per_1000 = s["n_argumenten"] * 1000 / s["totaal_tekens"] if s["totaal_tekens"] else 0.0
        claims_per_argument = s["n_claims"] / s["n_argumenten"] if s["n_argumenten"] else 0.0
        gem_quote_lengte = s["totaal_quote_lengte"] / s["n_argumenten"] if s["n_argumenten"] else 0.0
        gem_beurtlengte = s["totaal_tekens"] / s["n_documenten"] if s["n_documenten"] else 0.0
        tokens_per_zin = s["totaal_tokens"] / s["totaal_zinnen"] if s["totaal_zinnen"] else 0.0
        tokens_per_teken = s["totaal_tokens"] / s["totaal_tekens"] if s["totaal_tekens"] else 0.0

        rijen.append(
            {
                "naam": naam,
                "partij": partij or "",
                "n_documenten": s["n_documenten"],
                "n_argumenten": s["n_argumenten"],
                "argumenten_per_1000": argumenten_per_1000,
                "claims_per_argument": claims_per_argument,
                "gem_quote_lengte": gem_quote_lengte,
                "gem_beurtlengte": gem_beurtlengte,
                "gem_zinslengte": gem_zinslengte,
                "flesch_douma": flesch_douma,
                "lix": lix,
                "ttr": ttr,
                "tokens_per_zin": tokens_per_zin,
                "tokens_per_teken": tokens_per_teken,
            }
        )

    rijen.sort(key=lambda r: r[args.sorteer], reverse=True)

    reikwijdte = "alle topics" if args.alle_topics else f"topic '{args.topic}'"
    print(
        f"Verbositeit/dichtheid per spreker -- {reikwijdte}, "
        f"min. {args.min_documenten} sprekerbeurten, min. {args.min_argumenten} argumenten\n"
    )

    header = (
        f"{'spreker':<28}{'partij':<8}{'beurten':>8}{'argum.':>7}"
        f"{'arg/1000tek':>12}{'claims/arg':>11}{'quote-len':>10}"
        f"{'beurt-len':>10}{'zinslengte':>11}{'Flesch-D':>9}{'LIX':>6}{'TTR':>6}"
        f"{'tok/zin':>8}{'tok/tek':>8}"
    )
    print(header)
    print("-" * len(header))
    for r in rijen:
        print(
            f"{r['naam']:<28}{r['partij']:<8}{r['n_documenten']:>8}{r['n_argumenten']:>7}"
            f"{r['argumenten_per_1000']:>12.2f}{r['claims_per_argument']:>11.2f}"
            f"{r['gem_quote_lengte']:>10.0f}{r['gem_beurtlengte']:>10.0f}"
            f"{r['gem_zinslengte']:>11.1f}{r['flesch_douma']:>9.1f}{r['lix']:>6.1f}{r['ttr']:>6.2f}"
            f"{r['tokens_per_zin']:>8.1f}{r['tokens_per_teken']:>8.2f}"
        )

    print(
        "\narg/1000tek = argumenten per 1000 tekens sprekerbeurt (dichtheid), "
        "claims/arg = onderbouwingsdichtheid, quote-len/beurt-len in tekens, "
        "Flesch-Douma hoger = leesbaarder, LIX hoger = complexer, "
        "TTR = lexicale diversiteit (let op: gevoelig voor tekstlengte, dus "
        "alleen indicatief tussen sprekers met vergelijkbaar volume), "
        "tok/zin en tok/tek = tiktoken o200k_base-tokens per zin resp. per "
        "teken (hoger tok/tek = minder voorspelbare/complexere formuleringen)."
    )


if __name__ == "__main__":
    main()
