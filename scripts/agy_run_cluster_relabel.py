"""
Gerichte redactieslag op clusterlabels via agy (Docker/Gemini) -- issue #356.

Aanleiding: `make label-clusters` (qwen, lokaal) labelt elk cluster los, zonder
zicht op zijn siblings op hetzelfde niveau. Daardoor ontstaan botsingen die een
los-per-cluster-prompt nooit kan voorkomen: dezelfde naam op meerdere clusters
("Kamerprocedure" 5x op niveau 0) en vage kwalificatiewoorden die nauwelijks
onderscheiden ("Asielbeleid", "Belastingbeleid", "Coronabeleid" -- vrijwel elk
beleidsdomein kan zo heten). Dit script stuurt ALLE clusters van één niveau in
ÉÉN prompt naar agy, zodat het model de siblings kan zien en gericht alleen de
botsende/te vage namen vervangt door iets onderscheidends.

Herlabelt NIET alles opnieuw (de qwen-eerste-ronde blijft staan, wordt niet
overschreven) -- vraagt alleen om vervangingen voor de clusters die al
gevlagd zijn. Past niets automatisch toe (conform
docs/cluster-labeling-werkwijze.md: "nooit en bloc automatisch"): schrijft een
kandidaat-TOML-blok naar stdout + een los rapportbestand, voor handmatige
beoordeling vóór het in config/full/cluster_label_overrides.toml komt (zie
scripts/apply_cluster_label_overrides.py).

Gebruik:
    PYTHONPATH=. uv run python scripts/agy_run_cluster_relabel.py --level 0
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from pipeline.paths import REPO_ROOT
from scripts.check_cluster_label_quality import (
    find_duplicate_labels,
    find_parent_child_tautologies,
)

AGY_GEMINI_CONFIG_DIR = str(Path.home() / ".bipolariteit" / "agy_gemini_config")
CLUSTERS_PATH = REPO_ROOT / "data" / "plenair-map" / "clusters-full.json"
EXAMPLES_PATH = REPO_ROOT / "data" / "plenair-map" / "cluster-label-input-full.json"
OUTPUT_DIR = REPO_ROOT / "data" / "plenair-map"

# Zelfde vage-kwalificatiewoorden als in het #356-plan besproken ("alles is
# beleid") -- hier lokaal, niet in check_cluster_label_quality.py, omdat dit
# script ze alleen gebruikt om de prompt te annoteren, niet als losse
# gerapporteerde kwaliteitscheck (dat kan later, dit is de gerichte fix).
VAGUE_QUALIFIERS = ["beleid", "aanpak", "stelsel", "problematiek", "kwestie", "dossier"]


def run_agy(prompt, model):
    result = subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{AGY_GEMINI_CONFIG_DIR}:/home/agy/.gemini",
            "bipolariteit-agy",
            "agy", "--print", prompt,
            "--model", model,
            "--sandbox",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    return result.stdout.strip(), result.stderr.strip()


def _flag_notes(level_idx, summaries):
    """Korte, mensleesbare reden per cluster_id, alleen voor clusters die
    al gevlagd zijn -- zodat de prompt het model niet blind 36 namen laat
    herschrijven, maar wijst op specifiek wat te fixen is."""
    notes = {}
    for name, locs in find_duplicate_labels([summaries]).items():
        for _li, cid in locs:
            notes.setdefault(cid, []).append(f'deelt naam "{name}" met {len(locs) - 1} andere cluster(s)')
    for _li, cid, name, parent_name in find_parent_child_tautologies([summaries]):
        notes.setdefault(cid, []).append(f'herhaalt oudernaam "{parent_name}"')
    for s in summaries:
        lname = s["name"].lower()
        hit = next((v for v in VAGUE_QUALIFIERS if v in lname), None)
        if hit:
            notes.setdefault(s["cluster_id"], []).append(f'vaag kwalificatiewoord ("{hit}") voegt weinig onderscheid toe')
    return notes


def build_prompt(level_idx, summaries, examples_by_cluster):
    notes = _flag_notes(level_idx, summaries)
    lines = []
    for s in sorted(summaries, key=lambda s: s["cluster_id"]):
        cid = s["cluster_id"]
        examples = examples_by_cluster.get(str(cid), {"texts": []})
        snippet = " / ".join(t[:150] for t in examples["texts"][:2])
        entry = f'L{level_idx}-{cid}: "{s["name"]}" -- {s.get("duiding", "")[:200]}\n  voorbeeld: {snippet}'
        if cid in notes:
            entry += f"\n  TE FIXEN: {'; '.join(notes[cid])}"
        lines.append(entry)

    return f"""Je krijgt de {len(summaries)} top-niveau onderwerpclusters van een
UMAP-kaart van Tweede Kamer-plenaire debatten. Elk cluster is nu onafhankelijk
gelabeld (zonder zicht op de andere clusters), waardoor sommige namen botsen
of te vaag zijn geworden.

Clusters:
{chr(10).join(lines)}

Taak: geef ALLEEN voor de clusters met "TE FIXEN" een nieuwe, onderscheidende
naam. Regels:
- Bij voorkeur één woord; een tweede woord alleen als dat nodig is voor
  duidelijkheid.
- Geen namen van individuele Kamerleden, bewindspersonen of partijen.
- Diplomatieke, neutrale terminologie.
- Vermijd vage kwalificatiewoorden als "beleid"/"aanpak"/"stelsel" tenzij
  noodzakelijk -- bv. "Asiel" i.p.v. "Asielbeleid".
- De nieuwe naam mag niet gelijk zijn aan een van de 36 bestaande namen
  hierboven (ook niet de namen van clusters die je niet aanpast).
- Gebruik het voorbeeldfragment en de duiding om te bepalen wat dit cluster
  specifiek onderscheidt van de andere clusters met dezelfde botsende naam.

Antwoord in exact dit formaat, één regel per te wijzigen cluster, geen verdere
uitleg:
L{level_idx}-<cluster_id>: <nieuwe naam>"""


def parse_response(raw_text):
    proposals = {}
    for line in raw_text.splitlines():
        m = re.match(r"\s*L(\d+)-(\d+)\s*:\s*(.+)", line)
        if m:
            level_idx, cluster_id, name = int(m.group(1)), int(m.group(2)), m.group(3).strip()
            proposals[(level_idx, cluster_id)] = name
    return proposals


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", type=int, default=0)
    parser.add_argument("--model", default="gemini-3.6-flash-low")
    parser.add_argument("--clusters-json", type=Path, default=CLUSTERS_PATH)
    parser.add_argument("--examples-json", type=Path, default=EXAMPLES_PATH)
    parser.add_argument("--output", type=Path, default=None, help="rapport ook naar bestand schrijven")
    args = parser.parse_args()

    clusters_data = json.loads(args.clusters_json.read_text(encoding="utf-8"))
    summaries = clusters_data["levels"][args.level]
    examples_by_level = json.loads(args.examples_json.read_text(encoding="utf-8"))
    examples_by_cluster = examples_by_level[args.level]

    notes = _flag_notes(args.level, summaries)
    print(f"{len(notes)}/{len(summaries)} clusters op niveau {args.level} gevlagd om te fixen.\n")

    prompt = build_prompt(args.level, summaries, examples_by_cluster)
    stdout, stderr = run_agy(prompt, args.model)
    if not stdout:
        raise SystemExit(f"leeg antwoord van agy (stderr: {stderr[:500]})")

    proposals = parse_response(stdout)
    names_by_id = {s["cluster_id"]: s["name"] for s in summaries}

    report_lines = [f"# Kandidaat-hernoemingen niveau {args.level} (via agy, {args.model})", ""]
    for (level_idx, cluster_id), new_name in sorted(proposals.items()):
        old_name = names_by_id.get(cluster_id, "?")
        report_lines.append(f'"L{level_idx}-{cluster_id}" = "{new_name}"  # was: "{old_name}"')

    report = "\n".join(report_lines)
    print(report)
    print(f"\n{len(proposals)} voorstellen, {len(notes) - len(proposals)} gevlagde clusters zonder voorstel.")

    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"\nRapport geschreven naar {args.output}")


if __name__ == "__main__":
    main()
