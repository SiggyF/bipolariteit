"""Mapping tussen de drogreden-labels uit `fallacy`-kolom van
data/raw/elecdebate60to16/fallacy_second_version.csv (pierpaologoffredo/
ElecDeb60to20) en onze eigen tag-taxonomie (data/tags.toml, labelgroep
"Debatzetten"). Zie docs/eval-elecdebate.md voor de volledige
motivatie."""

# Alleen labels met een echte inhoudelijke tegenhanger in onze taxonomie
# worden gescoord.
FALLACY_TAG_MAP = {
    "Ad Hominem": "Debatzet-Persoon-Aanspreken",
    "Appeal to Emotion": "Debatzet-Gevoelens-Verwoorden",
}

# ELECDEBATE-labels zonder tegenhanger, bewust buiten scope van deze eval
# (geen gok-mapping). Toets: kan de tag worden toegekend zonder een
# inhoudelijk oordeel te vellen over of de onderliggende redenering klopt?
# Ad Hominem/Appeal to Emotion zijn zuiver structureel vast te stellen
# (FALLACY_TAG_MAP hierboven); de volgende drie niet, en zijn dus principieel
# uitgesloten (niet toevallig -- ons "we listen and we don't judge"-
# uitgangspunt in pipeline/db/schema.sql):
# - Appeal to Authority: hun eigen richtlijn vereist expliciet te beoordelen
#   of de aangehaalde autoriteit terecht overtuigt (zie guidelines/
#   fallacy_guidelines.pdf sectie 1) -- Walton-Expertise bestaat wel bij ons,
#   maar in het labelgroep "Redeneerschema" (legitiem, geen drogreden).
# - False Cause: vereist vaststellen dat een causale claim daadwerkelijk
#   onjuist is (correlatie != causaliteit) -- Walton-Causaal, idem hierboven.
# - Slippery Slope: vereist vaststellen dat het voorspelde extreme gevolg
#   daadwerkelijk implausibel is.
# Slogans voldoet wel aan de toets (structureel, geen inhoudelijk oordeel),
# maar is geen drogreden -- een slogan claimt geen redeneerfout, het is een
# stijlmiddel. Zie issue #67 voor een apart labelgroep "Stijlmiddelen".
UNMAPPED_FALLACIES = {"Appeal to Authority", "False Cause", "Slippery Slope", "Slogans"}
