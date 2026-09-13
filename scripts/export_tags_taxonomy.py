"""Zet config/tags.toml om naar frontend/src/lib/tagsTaxonomy.generated.ts.

De frontend heeft de volledige taxonomie (incl. beschrijvingen en tags zonder
toekenning) nodig voor de /tags-overzichtspagina, maar leest zelf geen TOML.
Opnieuw maken: uv run python scripts/export_tags_taxonomy.py
"""

import json
import tomllib
from pathlib import Path

from pipeline.taxonomy import DERIVED_LABELGROEPEN

BRON = Path(__file__).resolve().parent.parent / "config" / "tags.toml"
DOEL = Path(__file__).resolve().parent.parent / "frontend" / "src" / "lib" / "tagsTaxonomy.generated.ts"


def main() -> None:
    with BRON.open("rb") as f:
        toml = tomllib.load(f)

    perspectieven = []
    for perspectief in toml["perspectieven"]:
        labelgroepen = []
        for labelgroep in perspectief["labelgroepen"]:
            labelgroepen.append(
                {
                    "naam": labelgroep["naam"],
                    "beschrijving": labelgroep["beschrijving"],
                    "deterministic": labelgroep["naam"] in DERIVED_LABELGROEPEN,
                    "tags": [
                        {"sleutel": tag["sleutel"], "beschrijving": tag["beschrijving"]}
                        for tag in labelgroep["tags"]
                    ],
                }
            )
        perspectieven.append(
            {
                "naam": perspectief["naam"],
                "beschrijving": perspectief["beschrijving"],
                "labelgroepen": labelgroepen,
            }
        )

    DOEL.parent.mkdir(parents=True, exist_ok=True)
    inhoud = (
        "// GEGENEREERD -- niet met de hand aanpassen.\n"
        "// Bron: config/tags.toml.\n"
        "// Opnieuw maken: uv run python scripts/export_tags_taxonomy.py\n\n"
        "export interface TaxonomieTag {\n"
        "\tsleutel: string;\n"
        "\tbeschrijving: string;\n"
        "}\n\n"
        "export interface TaxonomieLabelgroep {\n"
        "\tnaam: string;\n"
        "\tbeschrijving: string;\n"
        "\t/** true voor Actor Type/Issue Arena/Parlementaire Context: automatisch\n"
        "\t * toegekend, niet door het LLM -- draagt daarom geen onderscheidend\n"
        "\t * signaal tussen partijen of personen (zie pipeline/taxonomy.py). */\n"
        "\tdeterministic: boolean;\n"
        "\ttags: TaxonomieTag[];\n"
        "}\n\n"
        "export interface TaxonomiePerspectief {\n"
        "\tnaam: string;\n"
        "\tbeschrijving: string;\n"
        "\tlabelgroepen: TaxonomieLabelgroep[];\n"
        "}\n\n"
        f"export const TAXONOMIE: TaxonomiePerspectief[] = {json.dumps(perspectieven, indent='\t', ensure_ascii=False)};\n"
    )
    DOEL.write_text(inhoud)

    aantal_tags = sum(len(lg["tags"]) for p in perspectieven for lg in p["labelgroepen"])
    print(f"{aantal_tags} tags weggeschreven naar {DOEL}")


if __name__ == "__main__":
    main()
