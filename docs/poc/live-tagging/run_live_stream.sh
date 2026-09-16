#!/usr/bin/env bash
# PoC (issue #113): restreamt de lopende Tweede Kamer-plenaire live naar een
# (unlisted) YouTube-teststream, met een live tekst-overlay (tag-chip +
# citaat) op basis van live_tagger.py's analyse van de live-ondertiteling.
#
# Icoon-badge-overlay (echte SVG-iconen uit de site) is bewust NIET meer
# onderdeel van deze keten -- werkte niet betrouwbaar in de volle live-keten
# (zmq/crop/overlay-mechanisme), zie issue #333 voor de vervolgpoging. De
# extra filters die dat kostte droegen ook bij aan de A/V-sync-vertraging
# hieronder (video liep door een langere keten dan audio), dus helemaal
# verwijderd i.p.v. alleen uitgeschakeld.
#
# Vereist:
#   - YT_STREAM_TOKEN (RTMP-stream-sleutel van de unlisted YouTube-teststream),
#     of OUTPUT_URL (bv. een lokaal .flv-pad) om zonder YouTube te testen
#   - HUGGINGFACE_INFERENCE_TOKEN (voor live_tagger.py, zie .devcontainer/.env.local)
#   - VIDEO_URL/AUDIO_URL/SUBTITLE_URL van de huidige uitzending (zie
#     docs/tk-data-sources-overview.md, live-restream-PoC-sectie, voor hoe je
#     die per debat opnieuw opzoekt via de Debat Direct agenda/detail-API)
#
# ffmpeg heeft -extension_picky 0 nodig op deze CDN (vos360.video): sinds de
# CVE-2023-6602-fix ("Be more picky on extensions") wijst ffmpeg's eigen
# HLS-demuxer elk .m4v/.m4a-segment af omdat die extensie niet in de default
# allowed_extensions-lijst staat voor het gedetecteerde mov/mp4-format --
# geen CDN-probleem, gewoon deze flag nodig (zie docs/tk-data-sources-overview.md).
set -euo pipefail

: "${VIDEO_URL:?zet VIDEO_URL (stream_0N/prog_index.m3u8 sub-playlist)}"
: "${AUDIO_URL:?zet AUDIO_URL (audio-sub-playlist, bv. stream_06)}"
: "${SUBTITLE_URL:?zet SUBTITLE_URL (nl_Live.m3u8 sub-playlist)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Bewust NIET in kaal /tmp: iets in deze devcontainer-omgeving ruimt losse
# /tmp-bestanden periodiek op, en ffmpeg's drawtext:reload=1 crasht de hele
# filterketen (en dus de stream) hard zodra het textfile eventjes ontbreekt
# -- vandaar OVERLAY_DIR, overschrijfbaar maar met een stabiele default.
OVERLAY_DIR="${OVERLAY_DIR:-$SCRIPT_DIR/.run}"
mkdir -p "$OVERLAY_DIR"
OVERLAY_PREFIX="$(mktemp -u -p "$OVERLAY_DIR" bipolariteit-live-overlay-XXXX)"
TAG_FILE="${OVERLAY_PREFIX}_tag.txt"
QUOTE_FILE="${OVERLAY_PREFIX}_quote.txt"
# Bronvermelding staat NIET meer in beeld -- gaat in de YouTube-streamdetails
# (titel/beschrijving) i.p.v. als on-screen watermerk. Let op: licentie-art.
# 4.2a vraagt om een "zichtbaar" logo/watermerk IN beeld als voorbeeld; een
# vermelding alleen in de streambeschrijving dekt dat strikt genomen niet
# volledig -- bewuste afweging van de gebruiker voor deze unlisted teststream.

# Merkkleur zoals gebruikt voor deze tags op de site zelf (perspectief
# "Filosofisch & Argumentatietheoretisch", zie frontend/src/lib/
# tagIcons.generated.ts) zodat de live-overlay bij de huisstijl aansluit.
TAG_KLEUR="0xB68235"
INK="0x221F1B"
CREME="0xF2EDE3"
FONT_BOLD="/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_ITALIC="/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"

cleanup() {
  [[ -n "${TAGGER_PID:-}" ]] && kill "$TAGGER_PID" 2>/dev/null || true
  # BEWUST geen rm van $TAG_FILE/$QUOTE_FILE hier: bleek de oorzaak van een
  # steeds terugkerende crash. Bij afsluiten (bv. door een timeout-signaal
  # tijdens testen) vuurt deze EXIT-trap eerder dan ffmpeg's eigen shutdown
  # klaar is, en verwijdert 'm de textfile net terwijl drawtext:reload=1 'm
  # nog één keer probeert te lezen -- "Cannot read file", hele stream stopt.
  # Kleine tekstbestandjes achterlaten is onschuldig (nieuwe run = nieuw
  # willekeurig gegenereerd OVERLAY_PREFIX, geen botsing).
}
trap cleanup EXIT

uv run --with pyzmq python "$SCRIPT_DIR/live_tagger.py" "$SUBTITLE_URL" "$OVERLAY_PREFIX" &
TAGGER_PID=$!
# live_tagger.py schrijft $TAG_FILE/$QUOTE_FILE pas na de eerste subtitle-poll;
# leeg aanmaken zodat drawtext:reload=1 niet start op een ontbrekend bestand.
: > "$TAG_FILE"
: > "$QUOTE_FILE"

# Tag-chip en citaat, allebei gecentreerd. reload=1 -- bij een lege
# tekstfile tekent drawtext simpelweg niets, geen aparte "leeg"-afhandeling.
FILTER="[0:v]drawtext=textfile=${TAG_FILE}:reload=1:fontfile=${FONT_BOLD}:fontcolor=${CREME}:fontsize=22:box=1:boxcolor=${TAG_KLEUR}@0.92:boxborderw=14:x=(w-text_w)/2:y=h-190[vtag]"
FILTER+=";[vtag]drawtext=textfile=${QUOTE_FILE}:reload=1:fontfile=${FONT_ITALIC}:fontcolor=${CREME}:fontsize=24:box=1:boxcolor=${INK}@0.78:boxborderw=14:x=(w-text_w)/2:y=h-140[vpts]"
# setpts=PTS-STARTPTS: video en audio zijn TWEE losse HLS-inputs die elk een
# eigen verbinding opzetten; als die verbindingen niet even lang duren om op
# te zetten, verschilt de PTS van het allereerste frame per input, en muxt
# ffmpeg ze dan met een vaste (niet-groeiende) offset t.o.v. elkaar. Beide
# normaliseren naar hun eigen t=0 (samen met asetpts via -af) haalt die
# vaste scheve-start-offset eruit -- zonder handmatig een vertraging te
# hoeven schatten.
FILTER+=";[vpts]setpts=PTS-STARTPTS[vout]"

OUTPUT_TARGET="${OUTPUT_URL:-rtmp://x.rtmp.youtube.com/live2/${YT_STREAM_TOKEN:?zet YT_STREAM_TOKEN (RTMP-stream-sleutel), of OUTPUT_URL voor een lokale testrun}}"

# ffmpeg is een enkele keer hard gecrasht op een tag/quote-textfile dat
# eventjes niet leesbaar was (zelfs in deze .run-map, niet kaal /tmp --
# oorzaak niet met zekerheid gevonden binnen de tijd die ervoor stond).
# I.p.v. daar verder achteraan te jagen: ffmpeg zelf herstartbaar maken, zo
# kan één transiënte hik nooit meer de hele uitzending beëindigen. set -e
# staat hier bewust uit, anders stopt het script zelf al bij de eerste
# afgebroken ffmpeg-poging.
set +e
while true; do
  : > "$TAG_FILE"
  : > "$QUOTE_FILE"
  ffmpeg -v warning \
    -extension_picky 0 -i "$VIDEO_URL" \
    -extension_picky 0 -i "$AUDIO_URL" \
    -filter_complex "$FILTER" \
    -map "[vout]" -map 1:a:0 \
    -af "aresample=async=1:min_hard_comp=0.100:first_pts=0" \
    -c:v libx264 -preset veryfast -tune zerolatency -b:v 850k -maxrate 850k -bufsize 1700k -pix_fmt yuv420p -g 50 \
    -c:a aac -b:a 128k -ar 44100 \
    -f flv "$OUTPUT_TARGET"
  status=$?
  if [[ $status -eq 0 ]]; then
    break
  fi
  echo "ffmpeg stopte met status $status, herstart over 2s..." >&2
  sleep 2
done
