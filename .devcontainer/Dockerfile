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
# ffmpeg: nodig om korte preview-clips uit de HLS-livestreams
# (raw_video_url, .m3u8) te snijden voor de video-shorts (issue #268) --
# ffmpeg kan zelf op tijdstip seeken/segmenten pakken uit een m3u8-manifest,
# dus geen aparte download-stap nodig.
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		python3.14 \
		python3.14-dev \
		sqlite3 \
		ffmpeg \
	&& rm -rf /var/lib/apt/lists/*

# Echte Google Chrome (i.p.v. alleen Playwright's eigen Chromium-download uit
# devcontainer.json's postCreateCommand): die open-source Chromium-build mist
# proprietary H.264/AAC-decoders, dus HLS-debatvideo's (Tweede Kamer-livestream)
# spelen daar niet af -- nodig om frontend/src/lib/clipExport.ts (issue #180)
# en videoplayback in het algemeen tegen een echte browser te kunnen
# verifiëren (bv. via Playwright met `channel: "chromium"`/executablePath op
# /usr/bin/google-chrome-stable). Chrome publiceert pas sinds 2026-Q3 een
# officiële arm64 .deb (chrome.com/download); curl i.p.v. het apt-repository
# toevoegen, want dat laatste vereist een los `apt-key`/keyring-stapje voor
# maar één pakket.
RUN curl -fsSL -o /tmp/google-chrome-stable.deb https://dl.google.com/linux/direct/google-chrome-stable_current_arm64.deb \
	&& apt-get update \
	&& apt-get install -y --no-install-recommends /tmp/google-chrome-stable.deb \
	&& rm -f /tmp/google-chrome-stable.deb \
	&& rm -rf /var/lib/apt/lists/*
