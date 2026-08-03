FROM mcr.microsoft.com/devcontainers/base:ubuntu

# De base image (of de uv-feature) laat het OS soms bij python3.14-minimal,
# dat delen van de stdlib mist (sqlite3, shlex, ...) waar de
# pipeline-scripts op leunen. `uv sync` pakt deze systeem-python i.p.v. een
# eigen managed build, dus zonder deze laag faalt zelfs `uv run pytest` met
# "No module named 'shlex'".
RUN apt-get update \
	&& apt-get install -y --no-install-recommends python3.14 \
	&& rm -rf /var/lib/apt/lists/*
