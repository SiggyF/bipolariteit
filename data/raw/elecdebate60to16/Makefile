.DEFAULT_GOAL := help

# Haalt de brondata voor het ELECDEBATE-evalharnas op (issue #62, zie
# docs/eval-elecdebate.md). Primaire bron: pierpaologoffredo/ElecDeb60to20 --
# de canonieke, volledige annotaties: full_components.csv dekt ALLE
# claim/premise-zinnen (niet alleen fallacieuze), full_speeches_new.csv geeft
# echte sprekersbeurten, fallacy_second_version.csv de drogreden-labels MET
# spreker+datum. scripts/convert_elecdebate.py gebruikt precies deze drie.
#
# pierpaologoffredo/FallacyDetection (`pos`/`conll`-targets) was de eerst
# gevonden bron, beperkter (alleen fallacieuze spans, geen sprekersbeurten) --
# blijft als legacy-target staan, wordt niet meer door de converter gebruikt.
#
# Alles landt in deze map, die als geheel gitignored is (data/raw/) --
# alleen dit Makefile zelf is ingecheckt.

ELECDEB60TO20 := https://raw.githubusercontent.com/pierpaologoffredo/ElecDeb60to20/main
FALLACYDETECTION := https://raw.githubusercontent.com/pierpaologoffredo/FallacyDetection/master
CONLL_FILES := train.conll dev.conll test.conll
POS_FILES := pos_train_set.csv pos_test_set.csv

.PHONY: help all components speeches fallacies pos conll paper clean

help: ## Toon deze lijst
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

all: components speeches fallacies ## Haal op wat scripts/convert_elecdebate.py gebruikt

components: ## Alle claim/premise-zinnen, ongeacht fallacy (full_components.csv, 44k+ rijen)
	curl -sSL -o full_components.csv "$(ELECDEB60TO20)/data/component_data/full_components.csv"

speeches: ## Volledige sprekersbeurten: datum, spreker, tekst (full_speeches_new.csv)
	curl -sSL -o full_speeches_new.csv "$(ELECDEB60TO20)/data/debates/full_speeches_new.csv"

fallacies: ## Drogreden-annotaties met spreker+datum (fallacy_second_version.csv)
	curl -sSL -o fallacy_second_version.csv "$(ELECDEB60TO20)/data/fallacy_second_version.csv"

paper: ## Goffredo et al. 2023 (EMNLP), ACL Anthology
	curl -sSL -o paper-goffredo-2023.pdf "https://aclanthology.org/2023.emnlp-main.684.pdf"

pos: ## (legacy, niet meer gebruikt door de converter) pos_*.csv uit FallacyDetection
	@for f in $(POS_FILES); do \
		echo "fetching $$f"; \
		curl -sSL -o $$f "$(FALLACYDETECTION)/data/$$f"; \
	done

conll: ## (legacy, niet meer gebruikt door de converter) token-level BIO-fallacybestanden
	@for f in $(CONLL_FILES); do \
		echo "fetching $$f"; \
		curl -sSL -o $$f "$(FALLACYDETECTION)/data/$$f"; \
	done

clean: ## Verwijder alle opgehaalde/gegenereerde bestanden (behalve dit Makefile)
	rm -f full_components.csv full_speeches_new.csv fallacy_second_version.csv \
		$(POS_FILES) $(CONLL_FILES) paper-goffredo-2023.pdf test.jsonl train.jsonl
