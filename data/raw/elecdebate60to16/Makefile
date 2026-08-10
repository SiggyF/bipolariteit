.DEFAULT_GOAL := help

# Haalt ELECDEBATE60TO16 op (issue #62, zie docs/eval-elecdebate.md): de
# CoNLL/BIO-fallacybestanden + de rijkere pos_*.csv (met arg_comp/arg_rel)
# uit pierpaologoffredo/FallacyDetection, plus de bijbehorende paper. Alles
# landt in deze map, die als geheel gitignored is (data/raw/) -- alleen dit
# Makefile zelf is ingecheckt.

REPO := https://raw.githubusercontent.com/pierpaologoffredo/FallacyDetection/master
CONLL_FILES := train.conll dev.conll test.conll
POS_FILES := pos_train_set.csv pos_test_set.csv

.PHONY: help all conll pos paper clean

help: ## Toon deze lijst
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

all: conll pos paper ## Haal alles op (CoNLL + pos_*.csv + paper)

conll: ## Token-level BIO-fallacybestanden (train/dev/test.conll)
	@for f in $(CONLL_FILES); do \
		echo "fetching $$f"; \
		curl -sSL -o $$f "$(REPO)/data/$$f"; \
	done

pos: ## Rijkere annotaties met arg_comp/arg_rel (pos_train_set.csv, pos_test_set.csv)
	@for f in $(POS_FILES); do \
		echo "fetching $$f"; \
		curl -sSL -o $$f "$(REPO)/data/$$f"; \
	done

paper: ## Goffredo et al. 2023 (EMNLP), ACL Anthology
	curl -sSL -o paper-goffredo-2023.pdf "https://aclanthology.org/2023.emnlp-main.684.pdf"

clean: ## Verwijder alle opgehaalde bestanden (behalve dit Makefile)
	rm -f $(CONLL_FILES) $(POS_FILES) paper-goffredo-2023.pdf train.jsonl test.jsonl
