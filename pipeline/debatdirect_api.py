"""
Gedeelde client voor Debat Direct's debat-detail-API, gebruikt door zowel
pipeline/fetch_subtitles.py (video.vodUrl/startsAt/endsAt) als
pipeline/fetch_debate_events.py (events/startedAt). Eén plek voor deze
HTTP-call zodat beide scripts 'm niet dubbel implementeren.

Zie docs/tk-data-sources-overview.md 5b/5c/5f voor de volledige uitleg van
deze route.
"""

DEBATE_API_URL = "https://api.debatdirect.tweedekamer.nl/debates/{id}"


def fetch_debate_detail(session, debatdirect_id):
    resp = session.get(DEBATE_API_URL.format(id=debatdirect_id), timeout=15)
    resp.raise_for_status()
    return resp.json()
