#!/usr/bin/env bash
# Probeert de twee bekende LM Studio-adressen (lokaal, of host.docker.internal
# vanuit een devcontainer) en print het eerste dat reageert. Stopt met een
# foutmelding op stderr en exitcode 1 als geen van beide bereikbaar is -- voor
# gebruik in de Makefile, zodat extract/tag/redactie niet zinloos falen op
# losse "connection refused"-fouten per document.
set -euo pipefail

KANDIDATEN=(
  "http://localhost:1234/v1"
  "http://host.docker.internal:1234/v1"
)

for url in "${KANDIDATEN[@]}"; do
  if curl -fsS --max-time 2 "$url/models" >/dev/null 2>&1; then
    echo "$url"
    exit 0
  fi
done

echo "FOUT: geen LLM-backend bereikbaar op localhost:1234 of host.docker.internal:1234." >&2
echo "Start LM Studio (of controleer of de devcontainer host.docker.internal kan bereiken, zie .devcontainer/devcontainer.json) en probeer opnieuw." >&2
exit 1
