"""
Draait de volledige argumentenboom-pipeline (issue #252) niet-interactief
via `agy` in Docker (docker/agy/Dockerfile): structureren + tweezijdige
redactie + samenvoegen + valideren, in één run. Schrijft het eindresultaat
naar data/export/argument-docs/<topic>-gemini-tree.json (zelfde bestandsnaam
als voorheen, ondanks dat het nu drie LLM-calls zijn i.p.v. één).

Drie stappen:
1. **Structureren** (pipeline/prompts/argument_tree_gemini.md): bouwt het
   argumentdocument zelf op (dezelfde functies als
   pipeline/export_argument_doc.py -- geen tussenbestand nodig) en laat
   Gemini een concept-boom bouwen (nodes/relations/coordinatieve_groepen/
   twijfelachtige_classificaties, zie pipeline/schemas/argument_tree.schema.json).
2. **Redactie, twee keer** (pipeline/prompts/boomredactie.md): een pro- en
   een contra-redacteur beoordelen onafhankelijk elke relatie uit stap 1 op
   diezelfde concept-boom.
3. **Samenvoegen + valideren** (pipeline/confrontatie_tree.py, zuivere
   Python, geen LLM): een relatie die door beide kanten onderschreven wordt
   telt als stevig, door precies één kant blijft ze staan maar gemarkeerd
   (weak_link), door geen van beide verdwijnt ze. Het resultaat wordt tegen
   het schema gevalideerd vóór het wegschrijven -- faalt de validatie, dan
   wordt niets weggeschreven.

Wordt aangeroepen door `make redactie TOPIC=<topic>`, dat er meteen ook
pipeline.build_confrontatie_export achteraan plakt.

In tegenstelling tot de extractie-/tagging-agy-scripts (honderden calls,
dus een goedkoop `flash-low`-model) zijn dit maar drie calls per topic -- de
default is daarom een zwaarder model. Zie
docs/design/argumentenboom/thema-en-samenvatting-workflow.md voor de
volledige workflow en hoe je itereert als de output niet scherp/leesbaar
genoeg is.

Vereist: `docker build -t bipolariteit-agy docker/agy` en een eenmalige
interactieve login (zie docs/handoff.md, sectie "Antigravity CLI (agy) in
Docker") -- dezelfde `~/.bipolariteit/agy_gemini_config`-sessie als de
extractie-/tagging-agy-scripts. Ontbreekt docker (bv. deze devcontainer-
sandbox) en staat er wel een ingelogde lokale agy-CLI op
`~/.gemini/bin/agy`, dan valt `_use_local_agy()` daar automatisch op terug
(zonder container-isolatie, met `--dangerously-skip-permissions` omdat er
geen wegwerpbare container is om binnen te blijven).

Het argumentdocument (tot ~1,5 MB voor stikstof-schaal topics) kan niet als
CLI-argument mee (OS-limiet op de grootte van een process-argument, macOS
faalt al met "Argument list too long" ruim onder 1,5 MB) en ook niet via
stdin (agy gebruikt stdin niet als input voor het model -- beide geprobeerd,
zie git-historie van dit bestand). In plaats daarvan wordt het document als
bestand in een tijdelijke map gemount en met `--add-dir` aan agy's workspace
toegevoegd -- alleen nodig voor de structureringsstap; de twee redactiestappen
werken op de al-geselecteerde concept-boom (~15-30 argumenten per kant), die
ruim binnen een gewoon `--print`-argument past.

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
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

from pipeline.confrontatie_tree import merge_reviews
from pipeline.db import db
from pipeline.export_argument_doc import build_document, fetch_stance_arguments
from pipeline.extract_arguments import _extract_json
from pipeline.periodes import PeriodeIndex

logger = logging.getLogger(__name__)

STRUCTURE_PROMPT_PATH = Path(__file__).parent.parent / "pipeline" / "prompts" / "argument_tree_gemini.md"
REDACTIE_PROMPT_PATH = Path(__file__).parent.parent / "pipeline" / "prompts" / "boomredactie.md"
TREE_SCHEMA_PATH = Path(__file__).parent.parent / "pipeline" / "schemas" / "argument_tree.schema.json"
GEMINI_TREE_DIR = Path(__file__).parent.parent / "data" / "export" / "argument-docs"
LOG_PATH = Path(__file__).parent.parent / "data" / "export" / "agy_confrontatie_tree.log"

# Buiten de repo (bevat een live OAuth-token, nooit in een git-repo laten
# staan) -- zelfde sessie als scripts/agy_run_extraction_batch.py. Als
# settings.json hier al bestaat (zie run_agy()) wordt die ook gebruikt --
# dezelfde map wordt 1-op-1 gemount op /home/agy/.gemini.
AGY_GEMINI_CONFIG_DIR = str(Path.home() / ".bipolariteit" / "agy_gemini_config")

# Eén call per topic i.p.v. honderden zoals bij extractie/tagging -- de
# extra kosten/tijd van een zwaarder model wegen hier niet zwaar, en dit is
# inhoudelijk lastiger werk (structureren + scherpe thema's + samenvatten,
# of het kritisch beoordelen daarvan) dan de per-document-extractie waar
# `flash-low` voor gekozen is.
DEFAULT_MODEL = "gemini-3.8-flash-medium"

CONTAINER_INPUT_DIR = "/data/input"
CONTAINER_OUTPUT_DIR = "/data/output"
DOC_FILENAME = "argumenten.md"
AGY_LOG_FILENAME = "agy.log"

# Fallback voor sandboxes zonder docker (bv. deze devcontainer, zie
# docs/handoff.md): een lokaal geïnstalleerde, al ingelogde agy-CLI buiten
# Docker om. Zelfde --print/--add-dir/--model-interface, maar zonder de
# container-isolatie -- de tijdelijke input-/outputmappen zijn dan gewoon
# echte paden op de host i.p.v. gemount op CONTAINER_INPUT_DIR/OUTPUT_DIR.
LOCAL_AGY_BIN = Path.home() / ".gemini" / "bin" / "agy"


def _use_local_agy():
    """docker ontbreekt in sommige sandboxes; val dan automatisch terug op
    LOCAL_AGY_BIN als die bestaat, in plaats van een cryptische
    "docker: command not found"-fout te geven."""
    return shutil.which("docker") is None and LOCAL_AGY_BIN.exists()

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
    scriptjes (`which` (om te checken welke interpreter beschikbaar is),
    `python3 -c "..."` (voornaamste aanpak), `perl` (fallback toen python3
    nog ontbrak in de Docker-image, zie docker/agy/Dockerfile) en
    `cat << 'EOF' > script.py` (scriptjes wegschrijven vóór ze uit te
    voeren). Elke `command(<naam>)`-regel whitelist op de commandonaam
    (prefix-matching, zie https://antigravity.google/docs/cli/permissions,
    voorbeeld "command(npm run (build|lint|test))") -- generieker dan de
    letterlijke, scriptspecifieke regel die de CLI's eigen "always allow"-
    optie zou opslaan (die matcht op de exacte scripttekst van dát ene
    scriptje, en werkt dus niet meer zodra agy een net iets andere aanroep
    genereert).

    Andere, eventueel al aanwezige instellingen in dit bestand (bv. de
    OAuth-sessie zelf staat elders in dezelfde AGY_GEMINI_CONFIG_DIR)
    blijven ongewijzigd staan."""
    rules = [
        f"read_file({CONTAINER_INPUT_DIR})",
        "command(which)",
        "command(python3)",
        "command(perl)",
        "command(cat)",
        # Ontdekt bij agy 1.1.27 (was 1.1.11 toen de regels hierboven werden
        # vastgesteld): voordat hij het document leest, verkent hij eerst de
        # workspace met `find` -- zowel op zoek naar bestanden die in de
        # instructietekst genoemd worden (bv. `boomredactie.md`, dat niet
        # gemount is en dus onvindbaar blijft, onschuldig) als breder
        # (`find /workspace /data /home/agy -name "*.py" -o ... | grep -v
        # ... | head -n 30`). Zonder deze regel loopt elke headless
        # (--print) aanroep hier al op vast, ver voordat de eigenlijke
        # structureer-/redactietaak begint.
        "command(find)",
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


def _run_agy_cmd(cmd, timeout, label):
    """Voert een kant-en-klare `docker run ... agy ...`-commando uit, leest
    agy's eigen --log-file-output terug (verwacht als laatste twee
    argumenten van cmd: het pad ernaartoe wordt door de caller al meegegeven
    via --log-file), en logt alles naar LOG_PATH. Gedeelde kern van
    run_agy() (structureringsstap, met gemount document) en
    run_agy_prompt() (redactiestappen, kleine boom past in --print)."""
    logger.info("%s -- commando: %s", label, " ".join(cmd))
    start = time.monotonic()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    elapsed = time.monotonic() - start
    _log_attempt(label, cmd, result.stdout, result.stderr, elapsed)
    if result.returncode != 0:
        logger.error("%s (returncode=%d) -- stderr:\n%s", label, result.returncode, result.stderr.strip())
    return result.stdout.strip(), result.stderr.strip(), elapsed


def run_agy(document, instructions, model, timeout, skip_permissions=False):
    """Structureringsstap: mount `document` als bestand in een tijdelijke,
    read-only map en voeg die met `--add-dir` toe aan agy's workspace -- zie
    moduledocstring voor waarom (te groot voor een CLI-argument of stdin).
    agy verwerkt het bestand zelf via shell-scriptjes (which/python3/perl/
    cat, zie _ensure_read_permission()), niet via een simpele file-read.

    `skip_permissions=True` is puur een noodgreep-optie voor als de scoped
    permissions.allow-regel onverwacht niet volstaat (bv. een tweede,
    onvoorziene tool die agy nodig blijkt te hebben) -- keurt dan ALLE
    tool-aanroepen goed, niet alleen file-reads. Risico blijft beperkt tot
    deze wegwerpbare container (--rm, alleen de auth-map en het read-only
    documentbestand gemount, geen toegang tot de rest van de repo/host)."""
    local = _use_local_agy()
    if not local:
        _ensure_read_permission()
    with tempfile.TemporaryDirectory(prefix="bipolariteit-agy-in-") as input_dir, \
         tempfile.TemporaryDirectory(prefix="bipolariteit-agy-out-") as output_dir:
        (Path(input_dir) / DOC_FILENAME).write_text(document)

        doc_path = f"{input_dir}/{DOC_FILENAME}" if local else f"{CONTAINER_INPUT_DIR}/{DOC_FILENAME}"
        instructions_with_path = (
            f"Het volledige argumentexport-document staat in het bestand "
            f"{doc_path} in je workspace -- lees dat bestand eerst, in "
            f"zijn geheel, voordat je de onderstaande opdracht uitvoert.\n\n{instructions}"
        )

        if local:
            log_path = Path(output_dir) / AGY_LOG_FILENAME
            cmd = [
                str(LOCAL_AGY_BIN), "--print", instructions_with_path,
                "--add-dir", input_dir,
                "--model", model,
                "--log-file", str(log_path),
                "--print-timeout", f"{timeout}s",
                "--dangerously-skip-permissions",
            ]
        else:
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
                "--print-timeout", f"{timeout}s",
            ]
            if skip_permissions:
                cmd.append("--dangerously-skip-permissions")

        stdout, stderr, elapsed = _run_agy_cmd(cmd, timeout, "structureren skip_permissions=" + str(skip_permissions))
        agy_log_path = Path(output_dir) / AGY_LOG_FILENAME
        agy_log = agy_log_path.read_text() if agy_log_path.exists() else "(--log-file leverde geen bestand op)"
        return stdout, f"{stderr}\n--- agy --log-file ({AGY_LOG_FILENAME}) ---\n{agy_log}", elapsed


def run_agy_prompt(prompt, model, timeout, label, skip_permissions=False):
    """Redactiestap: de concept-boom is klein genoeg (~15-30 argumenten per
    kant) om rechtstreeks in --print mee te geven, geen gemount bestand
    nodig zoals bij run_agy() (de structureringsstap, met het volledige
    argumentdocument)."""
    local = _use_local_agy()
    with tempfile.TemporaryDirectory(prefix="bipolariteit-agy-out-") as output_dir:
        if local:
            cmd = [
                str(LOCAL_AGY_BIN), "--print", prompt,
                "--model", model,
                "--log-file", str(Path(output_dir) / AGY_LOG_FILENAME),
                "--print-timeout", f"{timeout}s",
                "--dangerously-skip-permissions",
            ]
        else:
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{AGY_GEMINI_CONFIG_DIR}:/home/agy/.gemini",
                "-v", f"{output_dir}:{CONTAINER_OUTPUT_DIR}",
                "bipolariteit-agy",
                "agy", "--print", prompt,
                "--model", model,
                "--log-file", f"{CONTAINER_OUTPUT_DIR}/{AGY_LOG_FILENAME}",
                "--print-timeout", f"{timeout}s",
            ]
            if skip_permissions:
                cmd.append("--dangerously-skip-permissions")

        stdout, stderr, elapsed = _run_agy_cmd(cmd, timeout, f"{label} skip_permissions={skip_permissions}")
        agy_log_path = Path(output_dir) / AGY_LOG_FILENAME
        agy_log = agy_log_path.read_text() if agy_log_path.exists() else "(--log-file leverde geen bestand op)"
        return stdout, f"{stderr}\n--- agy --log-file ({AGY_LOG_FILENAME}) ---\n{agy_log}", elapsed


def _parse_or_die(stdout, stderr, label):
    if not stdout:
        raise SystemExit(
            f"leeg antwoord van agy ({label}) (stderr, eerste 2000 tekens: {stderr[:2000]}) -- volledige "
            f"output in {LOG_PATH}. Als dit een permissiefout is: whitelist de genoemde tool via settings.json "
            f"in {AGY_GEMINI_CONFIG_DIR} (zie run_agy()-docstring), of run desnoods opnieuw met "
            "--dangerously-skip-permissions."
        )
    try:
        return _extract_json(stdout)
    except Exception as exc:
        raise SystemExit(
            f"agy-output ({label}) is geen geldige JSON ({exc}); niet weggeschreven. Volledige output in "
            f"{LOG_PATH}.\n--- eerste 2000 tekens ---\n{stdout[:2000]}"
        )


def build_prompt(conn, topic_row, stances, vanaf):
    stances_by_name = {
        stance: fetch_stance_arguments(conn, topic_row["id"], stance, vanaf, limit=None) for stance in stances
    }
    document = build_document(topic_row, stances_by_name)
    instructions = STRUCTURE_PROMPT_PATH.read_text().format(topic=topic_row["name"])
    total = sum(len(v) for v in stances_by_name.values())
    return document, instructions, total


def run_redactie(structured, topic_name, kant, model, timeout, skip_permissions):
    tree_json = json.dumps(structured, ensure_ascii=False, indent=2)
    prompt = REDACTIE_PROMPT_PATH.read_text().format(topic=topic_name, kant=kant, tree_json=tree_json)
    stdout, stderr, elapsed = run_agy_prompt(prompt, model, timeout, f"redactie-{kant}", skip_permissions)
    logger.info("redactie-%s-call klaar in %.1fs", kant, elapsed)
    review = _parse_or_die(stdout, stderr, f"redactie-{kant}")
    if "beoordelingen" not in review:
        raise SystemExit(f"redactie-{kant}-output mist 'beoordelingen'-veld: {stdout[:500]}")
    return review


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="topic-slug, bv. stikstof")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"agy-model (default {DEFAULT_MODEL})")
    parser.add_argument("--stances", default="pro,contra", help="kommagescheiden lijst, default pro,contra")
    parser.add_argument("--vanaf", default=None, help="ISO-datum; overschrijft [verwerking].vanaf")
    parser.add_argument(
        "--out", default=None, help="uitvoerpad (default: data/export/argument-docs/<topic>-gemini-tree.json)"
    )
    parser.add_argument("--timeout", type=int, default=1800, help="timeout in seconden per agy-call (default 1800)")
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
        print("=== document (structureringsstap, via --add-dir bestand) ===")
        print(document)
        print("=== instructies (structureringsstap, --print) ===")
        print(instructions)
        logger.info("(--dry-run: geen agy-call)")
        return

    # 1. Structureren
    stdout, stderr, elapsed = run_agy(
        document, instructions, args.model, args.timeout, skip_permissions=args.dangerously_skip_permissions
    )
    logger.info("structureer-call klaar in %.1fs -- volledige in/output in %s", elapsed, LOG_PATH)
    structured = _parse_or_die(stdout, stderr, "structureren")
    for verplicht in ("nodes", "relations"):
        if verplicht not in structured:
            raise SystemExit(f"structureer-output mist '{verplicht}'-veld: {stdout[:500]}")
    structured.setdefault("coordinatieve_groepen", [])
    structured.setdefault("twijfelachtige_classificaties", [])

    # 2. Redactie, twee keer -- dezelfde concept-boom, onafhankelijk beoordeeld
    pro_review = run_redactie(
        structured, topic_row["name"], "pro", args.model, args.timeout, args.dangerously_skip_permissions
    )
    contra_review = run_redactie(
        structured, topic_row["name"], "contra", args.model, args.timeout, args.dangerously_skip_permissions
    )

    # 3. Samenvoegen + valideren -- geen LLM, puur Python (pipeline/confrontatie_tree.py)
    result = merge_reviews(structured, pro_review, contra_review)
    schema = json.loads(TREE_SCHEMA_PATH.read_text())
    try:
        Draft202012Validator(schema).validate(result)
    except ValidationError as exc:
        raise SystemExit(
            f"samengevoegde argumentenboom voldoet niet aan {TREE_SCHEMA_PATH.name}: {exc.message} "
            f"(pad: {list(exc.absolute_path)}). Niet weggeschreven."
        )

    dropped = len(structured["relations"]) - len(result["relations"])
    weak_link = sum(1 for r in result["relations"] if r["weak_link"])
    logger.info(
        "Redactie klaar: %d relaties gevalideerd, %d met weak_link, %d verworpen (door geen van beide redacteuren onderschreven).",
        len(result["relations"]), weak_link, dropped,
    )

    out_path = Path(args.out) if args.out else GEMINI_TREE_DIR / f"{args.topic}-gemini-tree.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info("Argumentenboom -> %s", out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
