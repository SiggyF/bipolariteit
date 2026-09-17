"""
PoC (issue #113): polt de live NL-ondertitel-track van Debat Direct,
verzamelt tekst in een glijdend venster, en laat er periodiek een lichte
LLM-tagging-prompt op los (Qwen/Qwen3.8-27B:ovhcloud, gratis via HF router --
zie pipeline/tag_single.py voor dezelfde backend in de batch-pipeline).
Schrijft de laatst gevonden tag + citaat naar twee tekstbestanden, die
ffmpeg via `drawtext=textfile=...:reload=1` in de live restream toont, en
zet via ffmpeg's zmq-filter het bijbehorende icoon-badge-overlay aan/uit
(zie run_live_stream.sh voor de volledige filterketen).

Bewust losstaand van pipeline/tag_arguments.py: die opereert op reeds
gesegmenteerde `arguments`-rijen uit het achteraf gepubliceerde VLOS-
verslag (batch, hele taxonomie, dask-parallel). Hier is de bron een
doorlopende, nog niet in spreekbeurten gesegmenteerde ondertitel-stream --
een nieuw pad ernaast, geen versnelling van de bestaande pipeline (zie
docs/tk-data-sources-overview.md, live-restream-PoC-sectie).

Gebruik:
    python live_tagger.py <subtitle_playlist_url> <overlay_txt_pad>
"""

import json
import logging
import os
import sys
import time
import tomllib
from pathlib import Path

import requests
import zmq

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from pipeline.hf_pricing import get_baseline_pricing, price_still_matches  # noqa: E402
from pipeline.llm_client import call_llm  # noqa: E402

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 2.0
TAG_EVERY_SECONDS = 8.0
WINDOW_SECONDS = 16.0
OVERLAY_CLEAR_AFTER_SECONDS = 40.0
# Tekst staat gecentreerd (x=(w-text_w)/2 in run_live_stream.sh) op de
# 960px-brede stream_03-render; ruim binnen de volle breedte houden zodat
# drawtext nooit buiten beeld loopt (geen automatische regelafbreking in
# ffmpeg's drawtext-filter).
MAX_TAG_LABEL_CHARS = 50
MAX_QUOTE_CHARS = 55


MODEL = "Qwen/Qwen3.8-27B:ovhcloud"
BASE_URL = "https://router.huggingface.co/v1"
# Zelfde patroon als pipeline/tag_single.py: een provider kan halverwege een
# lange run stilletjes gaan rekenen (zie hf_pricing.py-docstring) -- bij een
# live restream draait de tagger potentieel urenlang door, dus juist hier
# niet overslaan.
PRICE_CHECK_INTERVAL = 100
# Kleine subset van config/tags.toml -- kort genoeg te houden voor een
# prompt die elke 15s moet terugkomen; de volledige taxonomie (zie
# tag_arguments.py) is te groot voor een lage-latency live-prompt.
CANDIDATE_TAG_KEYS = [
    "Walton-Causaal", "Walton-Consequentie", "Walton-Expertise", "Walton-Analogie",
    "Debatzet-Persoon-Aanspreken", "Debatzet-Herformuleren", "Debatzet-Keuze-Aanscherpen",
    "Debatzet-Gevoelens-Verwoorden", "Debatzet-Cirkelredenering",
    "Stijl-Slogan", "Stijl-Herhaling", "Stijl-Retorische-Vraag", "Stijl-Godwin",
]


def _load_tag_catalogue():
    with open(REPO_ROOT / "config" / "tags.toml", "rb") as f:
        config = tomllib.load(f)
    by_key = {}
    for perspectief in config["perspectieven"]:
        for labelgroep in perspectief["labelgroepen"]:
            for tag in labelgroep["tags"]:
                by_key[tag["sleutel"]] = tag["beschrijving"]
    return {key: by_key[key] for key in CANDIDATE_TAG_KEYS if key in by_key}


def _build_prompt(fragment, catalogue):
    tag_lines = "\n".join(f"- {key}: {beschrijving}" for key, beschrijving in catalogue.items())
    return f"""Je analyseert een live fragment uit een Tweede Kamerdebat op mogelijke
argumentatie- of debattechnieken. Hier is de tag-catalogus:
{tag_lines}

Fragment (ruwe live-ondertiteling, kan stotter/afkappingen bevatten):
\"\"\"{fragment}\"\"\"

Geef ALLEEN geldige JSON terug, zonder uitleg: {{"tag": "<sleutel of null>", "citaat": "<kortste relevante zin uit het fragment, of null>"}}
Kies alleen een tag als je zeker bent; anders {{"tag": null, "citaat": null}}."""


def _parse_vtt_cues(vtt_text):
    lines = vtt_text.splitlines()
    cues = []
    for i, line in enumerate(lines):
        if "-->" in line and i + 1 < len(lines):
            text = lines[i + 1].strip()
            if text:
                cues.append(text)
    return cues


def poll_subtitles(playlist_url, session):
    base = playlist_url.rsplit("/", 1)[0]
    seen = set()
    while True:
        try:
            playlist_text = session.get(playlist_url, timeout=5).text
        except requests.RequestException as exc:
            logger.warning("subtitle-playlist ophalen mislukt: %s", exc)
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        for line in playlist_text.splitlines():
            line = line.strip()
            if not line.startswith("live/") or ".vtt" not in line:
                continue
            if line in seen:
                continue
            seen.add(line)
            try:
                vtt_text = session.get(f"{base}/{line}", timeout=5).text
            except requests.RequestException as exc:
                logger.warning("vtt-chunk ophalen mislukt: %s", exc)
                continue
            for cue in _parse_vtt_cues(vtt_text):
                yield time.monotonic(), cue

        if len(seen) > 1000:
            seen = set(list(seen)[-300:])
        time.sleep(POLL_INTERVAL_SECONDS)


def _truncate(text, max_chars):
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _format_tag_label(tag_key):
    # "Debatzet-Keuze-Aanscherpen" -> "DEBATZET · KEUZE AANSCHERPEN" (chip-
    # achtige opmaak: eerste segment als categorie, rest als label). Het
    # echte icoon staat als losse badge ernaast (zie IconController/
    # run_live_stream.sh), dus geen tekst-symbool hier nodig.
    parts = tag_key.split("-")
    categorie, label = parts[0], " ".join(parts[1:])
    return _truncate(f"{categorie.upper()} · {label.upper()}", MAX_TAG_LABEL_CHARS)


class IconController:
    """Stuurt via ffmpeg's zmq-filter aan welk icoon-badge zichtbaar is (zie
    run_live_stream.sh): alle badges staan naast elkaar in één sprite-PNG,
    een crop@iconselect-filter pakt daar één ICON_SIZE-vierkant uit (x =
    index * ICON_SIZE) en overlay@iconoverlay zet dat in beeld.

    Bewust GEEN los ffmpeg-image-input per tag (11 losse "-loop 1 -r 25"-
    inputs getest): elk zo'n input heeft zijn eigen klok, en met alle 11
    tegelijk in de keten haperde overlay's framesync volledig -- het icoon
    bleef onzichtbaar, ook met een hardcoded enable=1 zonder zmq. Met twee
    chained inputs werkte het wel, dus is dit een schaalprobleem van te veel
    onafhankelijk getimede branches, geen zmq-bug. Eén sprite-input (crop
    kiest alleen WELK stuk, geen extra klok erbij) lost dat op.

    Een los ffmpeg-image-input kan zelf niet hot-reloaded worden (leeg
    getest: bestand vervangen terwijl ffmpeg draait werd genegeerd), maar
    zmq mag WEL live filterparameters van een AL DRAAIENDE filter aanpassen
    -- de aanbevolen ffmpeg-weg voor dit "extern proces stuurt live iets in
    beeld aan".

    REQ/REP is strikt lock-step: een timeout laat de socket in een kapotte
    staat achter (geen nieuwe send() meer mogelijk) -- bij falen daarom de
    hele socket weggooien en opnieuw verbinden, in plaats van de live-loop
    te laten crashen op een gemiste badge-update."""

    def __init__(self, address, icon_index):
        self._address = address
        self._icon_index = icon_index  # tag_sleutel -> positie in de sprite
        self._icon_size = 88  # moet gelijk aan ICON_SIZE in run_live_stream.sh
        self._active_tag = None
        self._context = zmq.Context()
        self._socket = self._connect()

    def _connect(self):
        sock = self._context.socket(zmq.REQ)
        sock.setsockopt(zmq.RCVTIMEO, 2000)
        sock.setsockopt(zmq.LINGER, 0)
        sock.connect(self._address)
        return sock

    def _send(self, target, command, *args):
        message = " ".join([target, command, *args])
        try:
            self._socket.send_string(message)
            self._socket.recv_string()
            return True
        except zmq.ZMQError as exc:
            logger.warning("zmq-commando mislukt (%s): %s -- socket wordt herverbonden", message, exc)
            self._socket.close(linger=0)
            self._socket = self._connect()
            return False

    def set_active(self, tag_key):
        if tag_key == self._active_tag:
            return
        if tag_key is None:
            if self._send("overlay@iconoverlay", "enable", "0"):
                self._active_tag = None
            return
        index = self._icon_index.get(tag_key)
        if index is None:
            logger.warning("geen sprite-index voor tag %s, icoon-badge overgeslagen", tag_key)
            return
        # Eerst de crop-positie verzetten, dan pas tonen -- anders flitst
        # heel even het vorige icoon op de nieuwe plek (of andersom).
        if self._send("crop@iconselect", "x", str(index * self._icon_size)):
            if self._send("overlay@iconoverlay", "enable", "1"):
                self._active_tag = tag_key


class _NoIcons:
    """No-op vervanger voor IconController: icoon-badge-overlay is uit de
    live-keten gehaald (zie run_live_stream.sh, issue #333) zonder de
    IconController-code zelf te verwijderen, voor een latere vervolgpoging."""

    def set_active(self, tag_key):
        pass


def run(playlist_url, overlay_prefix, zmq_address=None, icon_index_file=None):
    tag_file = Path(f"{overlay_prefix}_tag.txt")
    quote_file = Path(f"{overlay_prefix}_quote.txt")
    tag_file.write_text("", encoding="utf-8")
    quote_file.write_text("", encoding="utf-8")

    api_key = os.environ["HUGGINGFACE_INFERENCE_TOKEN"]
    catalogue = _load_tag_catalogue()
    session = requests.Session()

    if icon_index_file and zmq_address:
        icon_index = json.loads(Path(icon_index_file).read_text(encoding="utf-8"))
        icons = IconController(zmq_address, icon_index)
    else:
        icons = _NoIcons()

    price_baseline = get_baseline_pricing(MODEL, BASE_URL)

    window = []  # list of (timestamp, cue_text)
    last_tag_at = 0.0
    last_overlay_write = 0.0
    tag_call_count = 0

    for timestamp, cue in poll_subtitles(playlist_url, session):
        window.append((timestamp, cue))
        window[:] = [(t, c) for t, c in window if timestamp - t <= WINDOW_SECONDS]

        if timestamp - last_tag_at < TAG_EVERY_SECONDS or not window:
            continue
        last_tag_at = timestamp
        tag_call_count += 1

        if tag_call_count % PRICE_CHECK_INTERVAL == 0 and not price_still_matches(MODEL, BASE_URL, price_baseline):
            logger.error("prijsstijging gedetecteerd, live-tagging gestopt (video/audio blijven wel doorlopen)")
            icons.set_active(None)
            tag_file.write_text("", encoding="utf-8")
            quote_file.write_text("", encoding="utf-8")
            return

        fragment = " ".join(c for _, c in window)
        response = None
        try:
            response = call_llm(
                BASE_URL, MODEL, _build_prompt(fragment, catalogue),
                reasoning_effort="none", timeout=20, max_tokens=500, api_key=api_key,
            )
            raw = response.content.strip()
            result = json.loads(raw.strip("`").removeprefix("json").strip())
        except Exception as exc:  # LLM/parsing hiccup mag de live-loop nooit stoppen
            logger.warning("tag-call mislukt of onparseerbaar: %s (raw=%r)", exc, response.content if response else None)
            continue

        tag = result.get("tag")
        citaat = result.get("citaat")
        if tag and tag in catalogue:
            tag_file.write_text(_format_tag_label(tag), encoding="utf-8")
            quote_text = f"“{_truncate(citaat, MAX_QUOTE_CHARS)}”" if citaat else ""
            quote_file.write_text(quote_text, encoding="utf-8")
            icons.set_active(tag)
            last_overlay_write = timestamp
            logger.info("tag: %s — %s", tag, citaat)
        elif timestamp - last_overlay_write > OVERLAY_CLEAR_AFTER_SECONDS:
            tag_file.write_text("", encoding="utf-8")
            quote_file.write_text("", encoding="utf-8")
            icons.set_active(None)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")
    if len(sys.argv) not in (3, 5):
        print(
            "gebruik: live_tagger.py <subtitle_playlist_url> <overlay_prefix_pad> [zmq_address icon_index_json]",
            file=sys.stderr,
        )
        sys.exit(1)
    zmq_address = sys.argv[3] if len(sys.argv) == 5 else None
    icon_index_file = sys.argv[4] if len(sys.argv) == 5 else None
    run(sys.argv[1], sys.argv[2], zmq_address, icon_index_file)
