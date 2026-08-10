"""
Meetexperiment voor issue #50: is het sneller om per document quote/claims en
tagging als twee turns in ÉÉN LLM-sessie te vragen (messages-array met het
turn-1-antwoord als voorgeschiedenis) dan als twee volledig losse calls?
Puur leesactie, schrijft niets naar de database en wijzigt geen
pipeline-bestanden of prompts.

Achterliggend idee: LM Studio's llama.cpp-server cachet de KV-state per slot
op basis van het langste gedeelde prefix van de `messages`-array. Stuurt turn 2
dezelfde messages (incl. het turn-1-antwoord) als prefix mee, dan hoeft die
prefix niet opnieuw geprocessed te worden -- mits de calls sequentieel op
dezelfde server lopen (geen andere aanroepen ertussen die de slot-cache
verdringen).

Vergelijkt drie dingen per document:
- baseline: de huidige, ongewijzigde extract_argument.md-prompt in één call
  (quote + claims + stance + typology, zoals de pipeline vandaag werkt).
- turn 1 (two-turn): een ingekorte "is dit een argument"-prompt, alleen
  quote_text/quote_context/claims.
- turn 2 (two-turn): in dezelfde sessie (messages van turn 1 + antwoord erbij)
  alsnog stance/typology/tags laten toekennen, met dezelfde tag-taxonomie als
  tag_argument.md.

Gebruik:
    uv run python scripts/experiment_two_turn_tagging.py
    uv run python scripts/experiment_two_turn_tagging.py --doc-ids 56,95,103
    uv run python scripts/experiment_two_turn_tagging.py --model qwen/qwen3.6-27b
"""
import argparse
import json
import statistics
import time

import requests

from pipeline.db import db
from pipeline.extract_arguments import (
    _build_prompt as _build_extract_prompt,
    _extract_json,
    _validate_argument,
    call_llm as call_llm_extract,
)
from pipeline.tag_arguments import build_tag_catalogue, load_valid_tags, _validate_tags

DEFAULT_DOC_IDS = list(range(40, 55))

PROMPT_IDENTIFY = """Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "{topic}". Spreker: {actor_name}{actor_party_suffix}.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "{topic}". Een argument heeft altijd twee delen: een standpunt ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn. Je bepaalt hier NOG NIET welk standpunt (pro/contra) het is -- alleen of er een argument is.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is.
- Citeer letterlijk uit de brontekst (quote_text) -- verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt, voeg dit samen tot één `quote_text` in plaats van het op te knippen in meerdere argumenten.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", dank-/welkomstwoorden. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- **Uitspraken over de behandeling van een voorstel leveren geen argument op**: aankondigen hoe een fractie stemt, een motie oordeel Kamer geven of ontraden, en verzoeken om een debat of een andere volgorde.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten.
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron noteer je als een claim, met alleen wat letterlijk gezegd is over de bron.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{{"arguments": [
  {{
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {{"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}}
    ]
  }}
]}}
```

Als er geen argumenten zijn: `{{"arguments": []}}`.

Brontekst (sprekerbeurt):
\"\"\"
{content}
\"\"\"
"""

PROMPT_TAG_FOLLOWUP = """Ken nu voor elk argument uit je vorige antwoord alsnog een standpunt en typologie toe, en tags uit onderstaande taxonomie.

Context over de pro/contra-dimensie van dit onderwerp:
{topic_description}

- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other".
- `stance`: het standpunt ligt altijd op de as tussen de twee polen hierboven -- niet tussen regering en oppositie. Leid het standpunt uitsluitend af uit de onderbouwing. Steunt de onderbouwing geen van beide polen, dan is het standpunt "unclear". Gaat het argument over een ander onderwerp, gebruik dan `stance: "ander_onderwerp"` en vul `ander_onderwerp` in.
- Voor tags: ken alleen tags toe die je uit onderstaande lijst kiest, letterlijk overgenomen (exacte sleutel). Bij "kies precies één": kies er ook echt maar één, of `null`. Bij "kies nul of meer": een lege lijst `[]` mag. Elke toegekende tag krijgt een `reden`.

Taxonomie:
{tag_catalogue}

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat per argument (zelfde volgorde als je vorige antwoord):

```
{{"arguments": [
  {{
    "stance": "pro" | "contra" | "unclear" | "ander_onderwerp",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "ander_onderwerp": "alleen bij stance ander_onderwerp, anders null",
    "tags": {tag_json_skeleton}
  }}
]}}
```
"""


def call_llm_messages(base_url, model, messages, reasoning_effort, timeout, max_tokens):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    resp = requests.post(f"{base_url}/chat/completions", json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"].get("content", "")
    usage = data.get("usage", {})
    return content, usage


def run_baseline(base_url, model, topic_name, topic_description, doc):
    prompt = _build_extract_prompt(topic_name, topic_description, doc["actor_name"], doc["actor_party"], doc["content"])
    start = time.monotonic()
    raw, usage, finish_reason = call_llm_extract(base_url, model, prompt, "none", 400.0, 4000)
    elapsed = time.monotonic() - start
    if finish_reason == "length":
        raise ValueError("antwoord afgekapt op max_tokens=4000")
    parsed = _extract_json(raw)
    valid = []
    for arg in parsed.get("arguments", []):
        try:
            _validate_argument(arg)
            valid.append(arg)
        except ValueError:
            pass
    return elapsed, valid


def run_two_turn(base_url, model, topic_name, topic_description, doc, tag_catalogue, tag_json_skeleton):
    actor_party_suffix = f" ({doc['actor_party']})" if doc["actor_party"] else ""
    prompt1 = PROMPT_IDENTIFY.format(
        topic=topic_name, actor_name=doc["actor_name"], actor_party_suffix=actor_party_suffix, content=doc["content"]
    )
    messages = [{"role": "user", "content": prompt1}]
    start1 = time.monotonic()
    raw1, _usage1 = call_llm_messages(base_url, model, messages, "none", 400.0, 4000)
    t1 = time.monotonic() - start1
    parsed1 = _extract_json(raw1)
    arguments = parsed1.get("arguments", [])

    if not arguments:
        return t1, None, []

    messages.append({"role": "assistant", "content": raw1})
    prompt2 = PROMPT_TAG_FOLLOWUP.format(
        topic_description=topic_description or topic_name,
        tag_catalogue=tag_catalogue,
        tag_json_skeleton=tag_json_skeleton,
    )
    messages.append({"role": "user", "content": prompt2})
    start2 = time.monotonic()
    raw2, _usage2 = call_llm_messages(base_url, model, messages, "none", 400.0, 2000)
    t2 = time.monotonic() - start2
    parsed2 = _extract_json(raw2)
    tagged = parsed2.get("arguments", [])
    return t1, t2, tagged


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--doc-ids", default=None, help="komma-gescheiden document-id's, default 40-54 (topic stikstof)")
    parser.add_argument("--model", default="qwen/qwen3.6-27b")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    args = parser.parse_args()

    doc_ids = [int(x) for x in args.doc_ids.split(",")] if args.doc_ids else DEFAULT_DOC_IDS

    conn = db.connect()
    topic_row = conn.execute("SELECT id, name, description FROM topics WHERE slug = 'stikstof'").fetchone()
    topic_id, topic_name, topic_description = topic_row["id"], topic_row["name"], topic_row["description"]

    docs = conn.execute(
        f"""SELECT d.id, d.content, a.name AS actor_name, a.party AS actor_party
            FROM documents d JOIN actors a ON a.id = d.actor_id
            WHERE d.topic_id = ? AND d.id IN ({','.join('?' * len(doc_ids))})
            ORDER BY d.id""",
        (topic_id, *doc_ids),
    ).fetchall()

    load_valid_tags(conn)  # valideert dat de taxonomie leesbaar is, resultaat hier niet nodig
    tag_catalogue, tag_json_skeleton = build_tag_catalogue(conn)

    print(f"Model: {args.model} | {len(docs)} documenten\n")

    baseline_times, two_turn_totals, t1_times, t2_times = [], [], [], []

    for doc in docs:
        try:
            b_elapsed, b_args = run_baseline(args.base_url, args.model, topic_name, topic_description, doc)
        except Exception as exc:
            print(f"[doc {doc['id']:>5}] {doc['actor_name']:<25} baseline FOUT: {exc}")
            continue
        baseline_times.append(b_elapsed)

        try:
            t1, t2, tt_args = run_two_turn(
                args.base_url, args.model, topic_name, topic_description, doc, tag_catalogue, tag_json_skeleton
            )
        except Exception as exc:
            print(f"[doc {doc['id']:>5}] {doc['actor_name']:<25} two-turn FOUT: {exc}")
            continue
        t1_times.append(t1)
        total = t1 + (t2 or 0.0)
        two_turn_totals.append(total)
        if t2 is not None:
            t2_times.append(t2)

        b_stances = [a["stance"] for a in b_args]
        tt_stances = [a.get("stance") for a in tt_args]
        match = "=" if (len(b_args), b_stances) == (len(tt_args), tt_stances) else "!="

        print(
            f"[doc {doc['id']:>5}] {doc['actor_name']:<25} "
            f"baseline={b_elapsed:5.1f}s | turn1={t1:5.1f}s turn2={(t2 or 0):5.1f}s totaal={total:5.1f}s | "
            f"{len(b_args)} vs {len(tt_args)} arg(en) {match} | baseline stances={b_stances} two-turn stances={tt_stances}"
        )

    print()
    if baseline_times and two_turn_totals:
        avg_baseline = statistics.mean(baseline_times)
        avg_two_turn = statistics.mean(two_turn_totals)
        print(f"Baseline: gem={avg_baseline:.1f}s min={min(baseline_times):.1f}s max={max(baseline_times):.1f}s")
        print(f"Two-turn: gem={avg_two_turn:.1f}s min={min(two_turn_totals):.1f}s max={max(two_turn_totals):.1f}s")
        if t1_times:
            print(f"  waarvan turn1 (identify): gem={statistics.mean(t1_times):.1f}s")
        if t2_times:
            print(f"  waarvan turn2 (tag, in sessie): gem={statistics.mean(t2_times):.1f}s")
        verschil = avg_baseline - avg_two_turn
        richting = "sneller" if verschil > 0 else "langzamer"
        print(f"Verschil: two-turn is gem. {abs(verschil):.1f}s per document {richting} dan baseline "
              f"({abs(verschil) / avg_baseline * 100:.0f}%).")


if __name__ == "__main__":
    main()
