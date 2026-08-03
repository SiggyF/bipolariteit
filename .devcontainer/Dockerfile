FROM mcr.microsoft.com/devcontainers/base:ubuntu

# De base image (of de uv-feature) laat het OS soms bij python3.14-minimal,
# dat delen van de stdlib mist (sqlite3, shlex, ...) waar de
# pipeline-scripts op leunen. `uv sync` pakt deze systeem-python i.p.v. een
# eigen managed build, dus zonder deze laag faalt zelfs `uv run pytest` met
# "No module named 'shlex'".
RUN apt-get update \
	&& apt-get install -y --no-install-recommends python3.14 \
	&& rm -rf /var/lib/apt/lists/*

# d2 (declaratieve diagramtaal, https://d2lang.com) -- rendert de
# argumentenboom (pipeline/render_argument_tree.py) naar SVG. Systeembreed
# geïnstalleerd (i.p.v. --prefix in $HOME) zodat het ook werkt los van het
# vscode-gebruikersprofiel.
RUN curl -fsSL https://d2lang.com/install.sh | sh -s -- --prefix /usr/local --force
