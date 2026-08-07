"""
Draait de argumentenboom-structurering (pipeline/prompts/argument_tree_gemini.md)
niet-interactief via `agy` in Docker (docker/agy/Dockerfile), i.p.v. het
argumentdocument + de prompt handmatig in een Gemini-chat te plakken.
Bouwt het argumentdocument zelf op (dezelfde functies als
pipeline/export_argument_doc.py -- geen tussenbestand nodig) en schrijft
Gemini's ruwe structurering direct naar
data/export/argument-docs/<topic>-gemini-tree.json. Wordt aangeroepen door
`make confrontatie-tree TOPIC=<topic>`, dat er meteen ook
pipeline.build_confrontatie_export achteraan plakt -- zonder handmatige
tussenstap.

In tegenstelling tot de extractie-/tagging-agy-scripts (honderden calls,
dus een goedkoop `flash-low`-model) is dit één call per topic -- de default
is daarom een zwaarder model. Zie
docs/design/argumentenboom/thema-en-samenvatting-workflow.md voor de volledige
workflow en hoe je itereert als de output niet scherp/leesbaar genoeg is.

Vereist: `docker build -t bipolariteit-agy docker/agy` en een eenmalige
interactieve login (zie docs/handoff.md, sectie "Antigravity CLI (agy) in
Docker") -- dezelfde `~/.bipolariteit/agy_gemini_config`-sessie als de
extractie-/tagging-agy-scripts.

Het argumentdocument (tot ~1,5 MB voor stikstof-schaal topics) kan niet als
CLI-argument mee (OS-limiet op de grootte van een process-argument, macOS
faalt al met "Argument list too long" ruim onder 1,5 MB) en ook niet via
stdin (agy gebruikt stdin niet als input voor het model -- beide geprobeerd,
zie git-historie van dit bestand). In plaats daarvan wordt het document als
bestand in een tijdelijke map gemount en met `--add-dir` aan agy's workspace
toegevoegd. Bij deze omvang leest agy het NIET via zijn gewone `read_file`-
tool, maar schrijft en draait hij zelf shell-scriptjes (`which`, `python3`,
`perl`, `cat << EOF > script.py`) om het te parsen/doorzoeken -- ontdekt door
een complete run eerst interactief te draaien (`docker run -it ... agy`,
zonder --print) en te zien welke permissies daadwerkelijk gevraagd werden.

Permissies: volgens https://antigravity.google/docs/cli/permissions bestaan
er zes permissie-acties (`read_file`, `write_file`, `command`, `read_url`,
`execute_url`, `mcp`); `_ensure_read_permission()` hieronder zet, idempotent,
gerichte `permissions.allow`-regels in agy's
`~/.gemini/antigravity-cli/settings.json` (binnen AGY_GEMINI_CONFIG_DIR,
dus meegemount als /home/agy/.gemini/antigravity-cli/settings.json) --
gescoped op commandonaam, in plaats van de bredere
`--dangerously-skip-permissions` ("keurt ALLE tool-aanroepen goed, incl.
file writes en command execution -- geef de voorkeur aan scoped
permissions.allow-regels", aldus de eigen documentatie). Draait ook zonder
`--sandbox`: die vraagt bij elk commando een losse "sandbox bypass"-
bevestiging (de binnen-container-sandboxmechaniek zit niet in
docker/agy/Dockerfile) zonder extra isolatie toe te voegen -- de
wegwerpbare Docker-container (--rm) is hier al de isolatiegrens.

Schrijft de volledige (niet-afgeknotte) stdout/stderr van elke poging, plus
agy's eigen `--log-file`-output (naar een apart schrijfbare gemounte map --
niet te vinden op het pad dat docs/handoff.md noemt, zie run_agy()), naar
data/export/agy_confrontatie_tree.log, zodat een eventuele permissiefout
z'n precieze toolnaam niet kwijtraakt in een teruggeknipte terminalregel.

Gebruik:
    PYTHONPATH=. uv run python scripts/agy_run_confrontatie_tree.py --topic stikstof
    PYTHONPATH=. uv run python scripts/agy_run_confrontatie_tree.py --topic stikstof --model gemini-3.6-flash-medium
"""

import argparse
import json
import logging
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from pipeline.db import db
from pipeline.export_argument_doc import build_document, fetch_stance_arguments
from pipeline.extract_arguments import _extract_json
from pipeline.periodes import PeriodeIndex

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "pipeline" / "prompts" / "argument_tree_gemini.md"
GEMINI_TREE_DIR = Path(__file__).parent.parent / "data" / "export" / "argument-docs"
LOG_PATH = Path(__file__).parent.parent / "data" / "export" / "agy_confrontatie_tree.log"

# Buiten de repo (bevat een live OAuth-token, nooit in een git-repo laten
# staan) -- zelfde sessie als scripts/agy_run_extraction_batch.py. Als
# settings.json hier al bestaat (zie run_agy()) wordt die ook gebruikt --
# dezelfde map wordt 1-op-1 gemount op /home/agy/.gemini.
AGY_GEMINI_CONFIG_DIR = str(Path.home() / ".bipolariteit" / "agy_gemini_config")

# Eén call per topic i.p.v. honderden zoals bij extractie/tagging -- de
# extra kosten/tijd van een zwaarder model wegen hier niet zwaar, en dit is
# inhoudelijk lastiger werk (structureren + scherpe thema's + samenvatten)
# dan de per-document-extractie waar `flash-low` voor gekozen is.
DEFAULT_MODEL = "gemini-3.6-flash-high"

CONTAINER_INPUT_DIR = "/data/input"
CONTAINER_OUTPUT_DIR = "/data/output"
DOC_FILENAME = "argumenten.md"
AGY_LOG_FILENAME = "agy.log"

# https://antigravity.google/docs/cli/permissions: settings.json leeft op
# ~/.gemini/antigravity-cli/settings.json -- binnen de gemounte
# AGY_GEMINI_CONFIG_DIR dus op dit relatieve pad.
SETTINGS_PATH = Path(AGY_GEMINI_CONFIG_DIR) / "antigravity-cli" / "settings.json"


def _ensure_read_permission():
    """Zet, idempotent, gerichte permissions.allow-regels in agy's
    settings.json, zodat hij het gemounte documentbestand mag lezen zonder
    --dangerously-skip-permissions nodig te hebben (die keurt ALLE tools
    goed). Zie moduledocstring.

    Deze regels zijn ontdekt door een complete, succesvolle run eerst
    handmatig interactief te draaien (`docker run -it ... agy`, zonder
    --print) en te kijken welke permissies daadwerkelijk gevraagd werden:
    bij een document van deze omvang (~1,5 MB) leest agy het NIET via zijn
    gewone `read_file`-tool, maar schrijft en draait hij zelf shell-
    scriptjes om het te parsen/chunken/doorzoeken -- `which` (om te
    checken welke interpreter beschikbaar is), `python3 -c "..."`
    (voornaamste aanpak), `perl` (fallback toen python3 nog ontbrak in de
    Docker-image, zie docker/agy/Dockerfile) en `cat << 'EOF' > script.py`
    (scriptjes wegschrijven vóór ze uit te voeren). Elke `command(<naam>)`-
    regel whitelist op de commandonaam (prefix-matching, zie
    https://antigravity.google/docs/cli/permissions, voorbeeld
    "command(npm run (build|lint|test))") -- generieker dan de letterlijke,
    scriptspecifieke regel die de CLI's eigen "always allow"-optie zou
    opslaan (die matcht op de exacte scripttekst van dát ene scriptje, en
    werkt dus niet meer zodra agy een net iets andere aanroep genereert).

    Andere, eventueel al aanwezige instellingen in dit bestand (bv. de
    OAuth-sessie zelf staat elders in dezelfde AGY_GEMINI_CONFIG_DIR)
    blijven ongewijzigd staan."""
    rules = [
        f"read_file({CONTAINER_INPUT_DIR})",
        "command(which)",
        "command(python3)",
        "command(perl)",
        "command(cat)",
    ]
    settings = json.loads(SETTINGS_PATH.read_text()) if SETTINGS_PATH.exists() else {}
    allow = settings.setdefault("permissions", {}).setdefault("allow", [])
    added = [rule for rule in rules if rule not in allow]
    if not added:
        return
    allow.extend(added)
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))
    logger.info("permissions.allow-regel(s) toegevoegd aan %s: %s", SETTINGS_PATH, added)


def _log_attempt(label, cmd, stdout, stderr, elapsed):
    """Schrijft de volledige (niet-afgeknotte) in- en output van een
    agy-poging naar LOG_PATH -- append, zodat je na een mislukte poging
    (bv. een permissiefout met de precieze toolnaam) niets terug hoeft te
    draaien om de details alsnog te zien."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(f"\n=== {label} | {datetime.now(timezone.utc).isoformat()} | {elapsed:.1f}s ===\n")
        f.write(f"cmd: {' '.join(cmd)}\n")
        f.write("--- stdout ---\n")
        f.write(stdout or "(leeg)")
        f.write("\n--- stderr ---\n")
        f.write(stderr or "(leeg)")
        f.write("\n")


def run_agy(document, instructions, model, timeout, skip_permissions=False):
    """Mount `document` als bestand in een tijdelijke, read-only map en voeg
    die met `--add-dir` toe aan agy's workspace -- zie moduledocstring voor
    waarom (te groot voor een CLI-argument of stdin). agy verwerkt het
    bestand zelf via shell-scriptjes (which/python3/perl/cat, zie
    _ensure_read_permission()), niet via een simpele file-read.

    `skip_permissions=True` is puur een noodgreep-optie voor als de scoped
    permissions.allow-regel onverwacht niet volstaat (bv. een tweede,
    onvoorziene tool die agy nodig blijkt te hebben) -- keurt dan ALLE
    tool-aanroepen goed, niet alleen file-reads. Risico blijft beperkt tot
    deze wegwerpbare container (--rm, alleen de auth-map en het read-only
    documentbestand gemount, geen toegang tot de rest van de repo/host)."""
    _ensure_read_permission()
    with tempfile.TemporaryDirectory(prefix="bipolariteit-agy-in-") as input_dir, \
         tempfile.TemporaryDirectory(prefix="bipolariteit-agy-out-") as output_dir:
        (Path(input_dir) / DOC_FILENAME).write_text(document)

        instructions_with_path = (
            f"Het volledige argumentexport-document staat in het bestand "
            f"{CONTAINER_INPUT_DIR}/{DOC_FILENAME} in je workspace -- lees dat bestand eerst, in "
            f"zijn geheel, voordat je de onderstaande opdracht uitvoert.\n\n{instructions}"
        )

        # Gewone argv-lijst (geen shell, geen quoting-gedoe): subprocess.run
        # geeft elk element letterlijk door aan execve, dus willekeurige
        # tekens in `instructions_with_path` (quotes, `$`, `*`, ...) kunnen
        # niet als shell-syntax geïnterpreteerd worden.
        #
        # Geen --sandbox: die vraagt bij ELK commando een losse "sandbox
        # bypass"-bevestiging (de binnen-container-sandboxmechaniek zit niet
        # in dit image), zonder dat het extra isolatie toevoegt -- de
        # wegwerpbare Docker-container (--rm) is hier al de isolatiegrens.
        #
        # --log-file naar een apart, schrijfbare (niet -ro) gemounte map:
        # agy's eigen debug-log bleek niet te leven op het pad dat
        # docs/handoff.md noemt (geen enkele "log"-directory gevonden onder
        # /home/agy, /tmp of /root in dit image) -- met --log-file kiezen we
        # zelf waar het terechtkomt, i.p.v. te gokken/zoeken.
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{AGY_GEMINI_CONFIG_DIR}:/home/agy/.gemini",
            "-v", f"{input_dir}:{CONTAINER_INPUT_DIR}:ro",
            "-v", f"{output_dir}:{CONTAINER_OUTPUT_DIR}",
            "bipolariteit-agy",
            "agy", "--print", instructions_with_path,
            "--add-dir", CONTAINER_INPUT_DIR,
            "--model", model,
            "--log-file", f"{CONTAINER_OUTPUT_DIR}/{AGY_LOG_FILENAME}",
        ]
        if skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        start = time.monotonic()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        elapsed = time.monotonic() - start

        agy_log_path = Path(output_dir) / AGY_LOG_FILENAME
        agy_log = agy_log_path.read_text() if agy_log_path.exists() else "(--log-file leverde geen bestand op)"
        stderr_with_log = f"{result.stderr}\n--- agy --log-file ({AGY_LOG_FILENAME}) ---\n{agy_log}"

        _log_attempt("skip_permissions=" + str(skip_permissions), cmd, result.stdout, stderr_with_log, elapsed)
        return result.stdout.strip(), stderr_with_log.strip(), elapsed


def build_prompt(conn, topic_row, stances, vanaf):
    stances_by_name = {
        stance: fetch_stance_arguments(conn, topic_row["id"], stance, vanaf, limit=None) for stance in stances
    }
    document = build_document(topic_row, stances_by_name)
    instructions = PROMPT_PATH.read_text().format(topic=topic_row["name"])
    total = sum(len(v) for v in stances_by_name.values())
    return document, instructions, total


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="topic-slug, bv. stikstof")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"agy-model (default {DEFAULT_MODEL})")
    parser.add_argument("--stances", default="pro,contra", help="kommagescheiden lijst, default pro,contra")
    parser.add_argument("--vanaf", default=None, help="ISO-datum; overschrijft [verwerking].vanaf")
    parser.add_argument(
        "--out", default=None, help="uitvoerpad (default: data/export/argument-docs/<topic>-gemini-tree.json)"
    )
    parser.add_argument("--timeout", type=int, default=1800, help="timeout in seconden voor de agy-call (default 1800)")
    parser.add_argument(
        "--dangerously-skip-permissions", action="store_true",
        help="voeg --dangerously-skip-permissions toe aan agy -- alleen als laatste redmiddel, zie run_agy()",
    )
    parser.add_argument("--dry-run", action="store_true", help="alleen de opgebouwde prompt printen, geen agy-call")
    args = parser.parse_args()

    stances = [s.strip() for s in args.stances.split(",") if s.strip()]

    conn = db.connect()
    topic_row = conn.execute("SELECT id, slug, name, description FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {args.topic}")

    vanaf = args.vanaf if args.vanaf is not None else PeriodeIndex().drempel
    document, instructions, total_args = build_prompt(conn, topic_row, stances, vanaf)
    conn.close()

    logger.info(
        "topic=%s model=%s %d argumenten, document %d tekens (--add-dir) + instructies %d tekens (--print)",
        topic_row["slug"], args.model, total_args, len(document), len(instructions),
    )

    if args.dry_run:
        print("=== document (via --add-dir bestand) ===")
        print(document)
        print("=== instructies (--print) ===")
        print(instructions)
        logger.info("(--dry-run: geen agy-call)")
        return

    stdout, stderr, elapsed = run_agy(
        document, instructions, args.model, args.timeout, skip_permissions=args.dangerously_skip_permissions
    )
    logger.info("agy-call klaar in %.1fs -- volledige in/output in %s", elapsed, LOG_PATH)

    if not stdout:
        raise SystemExit(
            f"leeg antwoord van agy (stderr, eerste 2000 tekens: {stderr[:2000]}) -- volledige output in {LOG_PATH}. "
            "Als dit een permissiefout is: whitelist de genoemde tool via settings.json in "
            f"{AGY_GEMINI_CONFIG_DIR} (zie run_agy()-docstring), of run desnoods opnieuw met "
            "--dangerously-skip-permissions."
        )

    try:
        parsed = _extract_json(stdout)
    except Exception as exc:
        raise SystemExit(
            f"agy-output is geen geldige JSON ({exc}); niet weggeschreven. Volledige output in {LOG_PATH}.\n"
            f"--- eerste 2000 tekens ---\n{stdout[:2000]}"
        )

    out_path = Path(args.out) if args.out else GEMINI_TREE_DIR / f"{args.topic}-gemini-tree.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2))
    logger.info("Gemini-tree -> %s", out_path)
    if "toelichting" in parsed:
        logger.info("Toelichting van Gemini: %s", parsed["toelichting"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
