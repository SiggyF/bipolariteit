"""
Rendert de boom-JSON van build_argument_tree.py naar een d2-diagram (SVG),
met een eigen stijl die de bestaande site-kleuren hergebruikt ("Ink & Rust",
zie frontend/src/styles/main.css --color-pro/--color-contra/--color-unclear).

Puur een render-stap -- geen LLM-calls, geen database. Leest
data/export/argument-trees/<slug>.json (geschreven door build_argument_tree.py)
en schrijft data/export/argument-trees/<slug>.svg.

Gebruik:
    uv run python -m pipeline.render_argument_tree --topic stikstof
"""

import argparse
import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Zelfde losse map als build_argument_tree.py (TREE_EXPORT_DIR) -- niet
# data/export/topics/ zelf, dat zou de "*.json" globs van de topic-pagina's
# door de hele frontend breken.
TREE_EXPORT_DIR = Path(__file__).parent.parent / "data" / "export" / "argument-trees"

QUOTE_LINE_WIDTH = 42
QUOTE_MAX_LEN = 200

STANCE_LABELS = {"pro": "Pro", "contra": "Contra", "unclear": "Onduidelijk"}

# "Ink & Rust" -- mirrors --color-pro/--color-contra/--color-unclear en
# --color-bg/--color-border (lichte modus) in frontend/src/styles/main.css.
# d2 bakt kleuren letterlijk in de SVG (geen CSS-custom-properties/theming
# runtime beschikbaar in deze d2-versie, zie devcontainer-Dockerfile), dus
# dit is een bewuste, statische spiegeling i.p.v. een live koppeling --
# als de site-kleuren wijzigen, moet dit bestand mee-updaten.
D2_CLASSES = """classes: {
  arg-pro: {
    style: {fill: "#eaf3f1"; stroke: "#1f6f66"; font-color: "#221f1b"}
  }
  arg-contra: {
    style: {fill: "#f6ece9"; stroke: "#9c3b32"; font-color: "#221f1b"}
  }
  arg-unclear: {
    style: {fill: "#efece5"; stroke: "#948a79"; font-color: "#221f1b"}
  }
  group: {
    style: {fill: "#f2efe7"; stroke: "#ddd5c4"; stroke-dash: 4; font-color: "#221f1b"}
  }
  stance-container: {
    style: {fill: "transparent"; stroke: "#ddd5c4"; font-color: "#221f1b"}
  }
}"""

# Struct-metafoor: een standpunt wordt van onderaf gestut door zijn
# argumenten (coördinatief/subordinatief -- "onderbouwt"-pijlen wijzen dus
# omhoog, richting het standpunt); een `direct_rebuttal` vanuit de andere
# stance is een aanval die dwars over die opbouw heen slaat ("weerlegt"-pijl,
# los gestyled, geen struct-kleur). `direction: up` laat d2 dat ook
# daadwerkelijk van onder naar boven opbouwen i.p.v. links-rechts.
DIRECTION = "direction: up"
OPPOSITION_STYLE = 'style.stroke: "#9c3b32"; style.stroke-dash: 3; style.stroke-width: 2; style.font-color: "#9c3b32"'


def _d2_escape(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _wrap(text, width=QUOTE_LINE_WIDTH):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines)


def _argument_label(arg):
    quote = arg["quote_text"]
    preview = quote if len(quote) <= QUOTE_MAX_LEN else quote[:QUOTE_MAX_LEN].rstrip() + "…"
    actor = arg.get("actor_name") or "onbekend"
    party = f" ({arg['actor_party']})" if arg.get("actor_party") else ""
    wrapped = _wrap(f'"{preview}"\n— {actor}{party}')
    # d2 breekt regels binnen een quoted string alleen op de letterlijke
    # `\n`-escape (twee tekens), niet op een echt newline-teken in de
    # brontekst -- vandaar de vertaalslag ná het escapen van backslash/quote.
    return _d2_escape(wrapped).replace("\n", "\\n")


def _shape_id(stance, argument_id):
    return f"a{stance}_{argument_id}"


def _group_id(stance, index):
    return f"g{stance}_{index}"


def _render_node(node, stance, arguments_by_id, lines, indent, group_counter, parent_shape_id, path_prefix, shape_paths):
    """Bouwt zowel de d2-tekst als `shape_paths` (argument_id -> volledig
    dotted d2-pad, bv. "pro.gpro_1.apro_12") op. Interne onderbouwt-pijlen
    kunnen korte, relatieve namen gebruiken (d2 lost ze lexicaal op binnen
    hetzelfde stance-blok); de weerleg-pijlen tussen pro en contra kunnen dat
    niet -- die worden buiten beide containers getekend en hebben daarom het
    volledige pad nodig, vandaar dat we dat hier al bijhouden."""
    pad = "  " * indent
    if "argument_id" in node:
        argument_id = node["argument_id"]
        shape_id = _shape_id(stance, argument_id)
        shape_paths[argument_id] = f"{path_prefix}.{shape_id}"
        lines.append(f'{pad}{shape_id}: "{_argument_label(arguments_by_id[str(argument_id)])}" {{')
        lines.append(f"{pad}  class: arg-{stance}")
        lines.append(f"{pad}}}")
        own_shape_id = shape_id
    else:
        group_counter[0] += 1
        own_shape_id = _group_id(stance, group_counter[0])
        own_path = f"{path_prefix}.{own_shape_id}"
        lines.append(f'{pad}{own_shape_id}: "{_d2_escape(node["label"])}" {{')
        lines.append(f"{pad}  class: group")
        for argument_id in node["argument_ids"]:
            member_shape_id = _shape_id(stance, argument_id)
            shape_paths[argument_id] = f"{own_path}.{member_shape_id}"
            lines.append(f'{pad}  {member_shape_id}: "{_argument_label(arguments_by_id[str(argument_id)])}" {{')
            lines.append(f"{pad}    class: arg-{stance}")
            lines.append(f"{pad}  }}")
        lines.append(f"{pad}}}")

    if parent_shape_id is not None:
        # Struct-metafoor: het kind stut de ouder, dus de pijl wijst omhoog
        # van kind naar ouder -- samen met `direction: up` (zie D2_CLASSES-omgeving)
        # bouwt d2 dit ook echt van onder (de losse argumenten) naar boven
        # (het standpunt) op.
        lines.append(f'{own_shape_id} -> {parent_shape_id}: "onderbouwt"')

    # Subordinatieve kinderen worden altijd als platte, stance-brede shapes
    # getekend (geen containment binnen een groep) -- alleen de "onderbouwt"-
    # pijl legt de relatie, dus path_prefix blijft ongewijzigd voor kinderen,
    # ook als de ouder zelf een groep-container is.
    for child in node.get("children") or []:
        _render_node(child, stance, arguments_by_id, lines, indent, group_counter, own_shape_id, path_prefix, shape_paths)


def build_d2_source(tree):
    """Puur tekstgeneratie, geen d2-CLI nodig -- apart getest van render_svg().
    Pro en contra staan als losse, van onderaf opgebouwde structuren naast
    elkaar; `direct_rebuttal`-links (tree["oppositions"]) worden als losse,
    afwijkend gestylede pijlen tussen die twee structuren getekend -- het
    "onderuithalen" van een specifieke stut door de andere kant."""
    lines = [DIRECTION, "", D2_CLASSES, ""]
    arguments_by_id = tree["arguments"]
    shape_paths = {}

    for stance_block in tree["stances"]:
        stance = stance_block["stance"]
        nodes = stance_block["nodes"]
        if not nodes:
            continue
        label = STANCE_LABELS.get(stance, stance)
        lines.append(f'{stance}: "{label}" {{')
        lines.append("  class: stance-container")
        group_counter = [0]
        for node in nodes:
            _render_node(
                node, stance, arguments_by_id, lines, indent=1, group_counter=group_counter,
                parent_shape_id=None, path_prefix=stance, shape_paths=shape_paths,
            )
        lines.append("}")
        lines.append("")

    for opposition in tree.get("oppositions") or []:
        a_path = shape_paths.get(opposition["argument_a_id"])
        b_path = shape_paths.get(opposition["argument_b_id"])
        if a_path is None or b_path is None:
            continue
        lines.append(f'{a_path} -> {b_path}: "weerlegt" {{{OPPOSITION_STYLE}}}')

    return "\n".join(lines)


def render_svg(d2_source, out_path, d2_bin=None, pad=40, theme=None):
    d2_bin = d2_bin or shutil.which("d2")
    if d2_bin is None:
        raise RuntimeError(
            "d2-CLI niet gevonden op $PATH. Installeer via "
            "`curl -fsSL https://d2lang.com/install.sh | sh -s --` (zie .devcontainer/Dockerfile)."
        )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".d2", delete=False) as tmp:
        tmp.write(d2_source)
        tmp_path = Path(tmp.name)

    try:
        cmd = [d2_bin, "--pad", str(pad)]
        if theme is not None:
            cmd += ["--theme", str(theme)]
        cmd += [str(tmp_path), str(out_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"d2 compileerfout:\n{result.stderr}")
    finally:
        tmp_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="topic-slug, bv. stikstof")
    parser.add_argument("--pad", type=int, default=40)
    parser.add_argument("--theme", type=int, default=None, help="d2-theme-ID (default: d2's eigen default)")
    args = parser.parse_args()

    tree_path = TREE_EXPORT_DIR / f"{args.topic}.json"
    if not tree_path.exists():
        raise SystemExit(
            f"geen boom-JSON gevonden op {tree_path} -- draai eerst "
            f"`uv run python -m pipeline.build_argument_tree --topic {args.topic}`"
        )
    tree = json.loads(tree_path.read_text())

    d2_source = build_d2_source(tree)
    out_path = TREE_EXPORT_DIR / f"{args.topic}.svg"
    render_svg(d2_source, out_path, pad=args.pad, theme=args.theme)
    logger.info("Boom-SVG -> %s", out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
