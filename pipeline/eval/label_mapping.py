"""Mapping tussen ELECDEBATE60TO16's drogreden-labels (BIO-tags in het
CoNLL-bronbestand, bv. "B-AdHominem") en onze eigen tag-taxonomie
(data/tags.toml, labelgroep "Dialectische Kwaliteit"). Zie
docs/eval-elecdebate.md voor de volledige motivatie."""

# Alleen labels met een echte inhoudelijke tegenhanger in onze taxonomie
# worden gescoord.
FALLACY_TAG_MAP = {
    "AdHominem": "Drogreden-Ad-Hominem",
    "AppealtoEmotion": "Drogreden-Bespelen-Publiek",
}

# ELECDEBATE-labels zonder tegenhanger, bewust buiten scope van deze eval
# (geen gok-mapping):
# - AppealtoAuthority/FalseCause hebben een structureel vergelijkbaar
#   Walton-schema (Walton-Expertise, Walton-Causaal), maar dat labelgroep is
#   een "legitiem argumentatieschema", geen drogreden -- gelijkstellen zou
#   ons "we listen and we don't judge"-uitgangspunt (pipeline/db/schema.sql)
#   tegenspreken.
# - Slipperyslope en Slogans hebben geen tegenhanger in data/tags.toml.
# Exacte schrijfwijze ("Slipperyslope", niet "SlipperySlope") overgenomen uit
# de Label-kolom van data/raw/elecdebate60to16/pos_train_set.csv.
UNMAPPED_FALLACIES = {"AppealtoAuthority", "FalseCause", "Slipperyslope", "Slogans"}
