.DEFAULT_GOAL := help

# Haalt de brondata voor het ELECDEBATE-evalharnas op (issue #62, zie
# docs/eval-elecdebate.md). Primaire bron: pierpaologoffredo/ElecDeb60to20 --
# de canonieke, volledige annotaties. scripts/convert_elecdebate.py gebruikt
# full_speeches_new.csv (sprekersbeurten), final_relation_graph.csv
# (Support/Attack-relaties tussen Claim/Premise-componenten -- daaruit
# reconstrueren we "claim MET onderbouwing", dezelfde eenheid als onze eigen
# extractie) en fallacy_second_version.csv (drogreden-labels MET
# spreker+datum).
#
# `components` (full_components.csv, alle Claim/Premise-zinnen los van elkaar)
# wordt niet meer gebruikt door de converter -- dat matcht niet op onze eigen
# argumentdefinitie (stance + onderbouwing in één eenheid), zie
# docs/eval-elecdebate.md. Blijft als los, niet-gebruikt referentietarget.
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

.PHONY: help all speeches relations fallacies components pos conll paper guidelines clean

help: ## Toon deze lijst
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

all: speeches relations fallacies ## Haal op wat scripts/convert_elecdebate.py gebruikt

speeches: ## Volledige sprekersbeurten: datum, spreker, tekst (full_speeches_new.csv)
	curl -sSL -o full_speeches_new.csv "$(ELECDEB60TO20)/data/debates/full_speeches_new.csv"

relations: ## Support/Attack/Equivalent-relaties tussen componenten (final_relation_graph.csv)
	curl -sSL -o final_relation_graph.csv "$(ELECDEB60TO20)/data/final_relation_graph.csv"

fallacies: ## Drogreden-annotaties met spreker+datum (fallacy_second_version.csv)
	curl -sSL -o fallacy_second_version.csv "$(ELECDEB60TO20)/data/fallacy_second_version.csv"

components: ## (referentie, niet gebruikt door de converter) alle claim/premise-zinnen los (full_components.csv)
	curl -sSL -o full_components.csv "$(ELECDEB60TO20)/data/component_data/full_components.csv"

paper: ## Goffredo et al. 2023 (EMNLP), ACL Anthology
	curl -sSL -o paper-goffredo-2023.pdf "https://aclanthology.org/2023.emnlp-main.684.pdf"

guidelines: ## Haddadan, Cabrio & Villata's annotatierichtlijn (Claim/Premise-definities, zie docs/eval-elecdebate.md)
	curl -sSL -o ElectDeb60To16_Guidelines.pdf "https://raw.githubusercontent.com/ElecDeb60To16/Dataset/master/ElectDeb60To16_Guidelines.pdf"

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
	rm -f full_speeches_new.csv final_relation_graph.csv fallacy_second_version.csv full_components.csv \
		$(POS_FILES) $(CONLL_FILES) paper-goffredo-2023.pdf ElectDeb60To16_Guidelines.pdf test.jsonl train.jsonl
