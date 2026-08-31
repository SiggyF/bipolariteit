FROM mcr.microsoft.com/devcontainers/base:ubuntu

# De base image (of de uv-feature) laat het OS soms bij python3.14-minimal,
# dat delen van de stdlib mist (sqlite3, shlex, ...) waar de
# pipeline-scripts op leunen. `uv sync` pakt deze systeem-python i.p.v. een
# eigen managed build, dus zonder deze laag faalt zelfs `uv run pytest` met
# "No module named 'shlex'".
# python3.14-dev (Python.h) is nodig om hdbscan (experiments-groep,
# scripts/experiment_umap_documents.py) uit source te bouwen -- er is geen
# prebuilt aarch64/py3.14-wheel, dus zonder deze laag faalt `uv sync
# --all-groups`/`--group experiments` op een gcc-fout.
RUN apt-get update \
	&& apt-get install -y --no-install-recommends python3.14 python3.14-dev sqlite3 \
	&& rm -rf /var/lib/apt/lists/*
