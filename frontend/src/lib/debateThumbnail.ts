// TS-poort van pipeline/build_static_data.py `_thumbnail_url`: bouwt een
// still-URL via Debat Direct's eigen scrub-bar-thumbnail-endpoint (zie
// docs/tk-data-sources-overview.md 5e). De Python-versie berekent 1
// representatief beeld per *topic* (eerste argument met een gematchte
// videospanne); deze versie doet hetzelfde per *debat*, voor de
// "Uitgelicht"-kaarten op de homepage. Geen gedeelde implementatie met de
// pipeline (andere taal), dus bewust hier apart uitgeschreven -- bij een
// wijziging aan het endpoint-formaat moeten beide kanten worden aangepast.

const NAIVE_LOCAL_RE = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/;

function pad(n: number, width = 2): string {
	return String(n).padStart(width, "0");
}

// Offset (in minuten t.o.v. UTC) die Europe/Amsterdam heeft op het gegeven
// UTC-tijdstip -- positief voor zomertijd (+120) en wintertijd (+60).
function amsterdamOffsetMinutes(utcMs: number): number {
	const parts = Object.fromEntries(
		new Intl.DateTimeFormat("en-US", {
			timeZone: "Europe/Amsterdam",
			hourCycle: "h23",
			year: "numeric",
			month: "2-digit",
			day: "2-digit",
			hour: "2-digit",
			minute: "2-digit",
			second: "2-digit",
		})
			.formatToParts(new Date(utcMs))
			.map((p) => [p.type, p.value]),
	);
	const asIfUtc = Date.UTC(
		Number(parts.year),
		Number(parts.month) - 1,
		Number(parts.day),
		Number(parts.hour),
		Number(parts.minute),
		Number(parts.second),
	);
	return Math.round((asIfUtc - utcMs) / 60_000);
}

function formatOffset(minutes: number): string {
	const sign = minutes >= 0 ? "+" : "-";
	const abs = Math.abs(minutes);
	return `${sign}${pad(Math.floor(abs / 60))}${pad(abs % 60)}`;
}

/** `videoUrl` is document.video_url (Debat Direct-paginalink, niet het HLS-
 * manifest): het zaal-pad-segment (locationId) zit daarin verwerkt, zie
 * dezelfde aanname in de Python-versie. `publishedAt` is naive lokale
 * Amsterdam-tijd zonder offset (types.ts). */
export function debateThumbnailUrl(videoUrl: string | null, publishedAt: string | null, startSeconds: number | null): string | null {
	if (!videoUrl || !publishedAt || startSeconds === null) return null;

	let locationId: string;
	try {
		const segments = new URL(videoUrl).pathname.split("/").filter(Boolean);
		// pathname zonder leidende "/" heeft locationId op index 2 (jaar-maand-dag=0,
		// zaaltype=1, locationId=2) -- gelijk aan Python's parts[5] op de volledige
		// URL (die de twee lege segmenten vóór het pad meetelt).
		locationId = segments[2];
		if (!locationId) return null;
	} catch {
		return null;
	}

	const match = NAIVE_LOCAL_RE.exec(publishedAt);
	if (!match) return null;
	const [, year, month, day, hour, minute, second] = match.map(Number);

	// Naive wall-clock-optelling: seconden bij de losse velden optellen via
	// UTC-epoch-rekenkunde (geen echte UTC, alleen een correcte manier om
	// dag-/maandovergangen te laten rollen), exact zoals Python's
	// `timedelta`-optelling op een naive datetime.
	const afterOffsetMs = Date.UTC(year, month - 1, day, hour, minute, second) + startSeconds * 1000;
	const wallClock = new Date(afterOffsetMs);

	// Twee-staps-benadering om de DST-offset van dát (mogelijk verschoven)
	// tijdstip te bepalen: eerste gok behandelt de wall-clock-tijd zelf als
	// UTC-tijdstip om een offset te schatten, tweede stap herhaalt dat op het
	// resulterende kandidaat-UTC-tijdstip. Correct behalve in het uur rond een
	// klimzet-moment zelf, wat voor dit doel (illustratieve thumbnail) geen
	// probleem is.
	const offsetGuess = amsterdamOffsetMinutes(afterOffsetMs);
	const offset = amsterdamOffsetMinutes(afterOffsetMs - offsetGuess * 60_000);

	const dateStr = `${wallClock.getUTCFullYear()}-${pad(wallClock.getUTCMonth() + 1)}-${pad(wallClock.getUTCDate())}`;
	const timeStr = `${pad(wallClock.getUTCHours())}:${pad(wallClock.getUTCMinutes())}:${pad(wallClock.getUTCSeconds())}`;
	return `https://livestreaming-thumb.b67buv2.tweedekamer.nl/${locationId}/1080/${dateStr}/${timeStr}${formatOffset(offset)}.jpg`;
}
