"""
Schrijft elk VideoFragmentItem als een geclipt .mp4-bestand + metadata-JSON
naar data/raw/debatdirect-fragments/<terms_slug>/, in hetzelfde ruwe-
crawl-formaat (mediabestand + sidecar-JSON) als tweede_kamer's
RawFilePipeline. Namespacing per zoekterm-combinatie houdt treffers van
losse crawls uit elkaar.

Het clippen zelf gebeurt hier (niet als aparte, latere stap) via ffmpeg op
het ruwe HLS-manifest -- bewust `-allowed_extensions ALL -extension_picky
0`: de CDN's fMP4-segmenten (.m4v/.m4a) worden door ffmpeg's hls-demuxer
anders afgewezen met "detected format ... mismatches allowed extensions
in url", geverifieerd geen serverfout (HTTP 200 op het segment zelf),
puur ffmpeg's extensie-strictheid.

Idempotent via het bestaan van het .mp4-bestand (net als de VTT-cache van
pipeline/fetch_subtitles.py in de hoofdrepo) -- geen database-boekhouding
nodig.
"""

import json
import subprocess

from .debatdirect import slugify
from .paths import RAW_DIR


class VideoFragmentPipeline:
    def open_spider(self, spider):
        RAW_DIR.mkdir(parents=True, exist_ok=True)

    def process_item(self, item, spider):
        terms_slug = slugify("-".join(item["terms"]))
        out_dir = RAW_DIR / terms_slug
        out_dir.mkdir(parents=True, exist_ok=True)

        speaker_slug = slugify(item.get("speaker") or "onbekend")
        filename = f"{item['debate_date']}_{speaker_slug}_{slugify(item['event_start'])}"
        video_path = out_dir / f"{filename}.mp4"
        meta_path = out_dir / f"{filename}.json"

        if video_path.exists():
            spider.logger.info(f"al aanwezig, overgeslagen: {video_path.name}")
            return item

        cmd = [
            "ffmpeg", "-y", "-allowed_extensions", "ALL", "-extension_picky", "0",
            "-ss", f"{item['clip_start_seconds']:.2f}", "-t", f"{item['clip_duration_seconds']:.2f}",
            "-i", item["manifest_url"], str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not video_path.exists():
            spider.logger.error(f"ffmpeg mislukt voor {video_path.name}: {result.stderr[-2000:]}")
            return item

        meta_path.write_text(
            json.dumps(
                {
                    "terms": item["terms"],
                    "debate_id": item["debate_id"],
                    "debate_title": item["debate_title"],
                    "debate_date": item["debate_date"],
                    "video_url": item["video_url"],
                    "deep_link_url": item["deep_link_url"],
                    "event_type": item["event_type"],
                    "event_start": item["event_start"],
                    "speaker": item["speaker"],
                    "party": item["party"],
                    "highlight": item["highlight"],
                    "clip_start_seconds": item["clip_start_seconds"],
                    "clip_duration_seconds": item["clip_duration_seconds"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        spider.logger.info(f"gedownload: {video_path.name} ({item['clip_duration_seconds']:.0f}s vanaf {item['clip_start_seconds']:.0f}s)")
        return item
