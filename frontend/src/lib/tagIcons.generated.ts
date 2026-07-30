// GEGENEREERD -- niet met de hand aanpassen.
// Bron: docs/design/tag-iconografie/tag-styles.json + lucide-static.
// Opnieuw maken: cd frontend && node scripts/build_tag_icons.mjs

/** Lucide-iconen als ECharts-padstring. Lijntekeningen: teken ze met
 *  itemStyle.borderColor en een doorzichtige vulling, niet met .color. */
export const ICOON_PAD: Record<string, string> = {
	"arrow-left-right": "M0 0 M24 24 M8 3 4 7l4 4M4 7h16m16 21 4-4-4-4M20 17H4",
	"badge-check": "M0 0 M24 24 M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Zm9 12 2 2 4-4",
	"banknote": "M0 0 M24 24 M4 6h16a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-16a2 2 0 0 1 -2 -2v-8a2 2 0 0 1 2 -2ZM10 12a2 2 0 1 0 4 0a2 2 0 1 0 -4 0M6 12h.01M18 12h.01",
	"bar-chart-2": "M0 0 M24 24 M5 21v-6M12 21V3M19 21V9",
	"brain": "M0 0 M24 24 M12 18V5M15 13a4.17 4.17 0 0 1-3-4 4.17 4.17 0 0 1-3 4M17.598 6.5A3 3 0 1 0 12 5a3 3 0 1 0-5.598 1.5M17.997 5.125a4 4 0 0 1 2.526 5.77M18 18a4 4 0 0 0 2-7.464M19.967 17.483A4 4 0 1 1 12 18a4 4 0 1 1-7.967-.517M6 18a4 4 0 0 1-2-7.464M6.003 5.125a4 4 0 0 0-2.526 5.77",
	"briefcase": "M0 0 M24 24 M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16M4 6h16a2 2 0 0 1 2 2v10a2 2 0 0 1 -2 2h-16a2 2 0 0 1 -2 -2v-10a2 2 0 0 1 2 -2Z",
	"building-2": "M0 0 M24 24 M10 12h4M10 8h4M14 21v-3a2 2 0 0 0-4 0v3M6 10H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2M6 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16",
	"calendar-clock": "M0 0 M24 24 M16 14v2.2l1.6 1M16 2v3M21 7.338V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h2.338M3 9h5.859M8 2v3M10 16a6 6 0 1 0 12 0a6 6 0 1 0 -12 0",
	"camera": "M0 0 M24 24 M13.997 4a2 2 0 0 1 1.76 1.05l.486.9A2 2 0 0 0 18.003 7H20a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h1.997a2 2 0 0 0 1.759-1.048l.489-.904A2 2 0 0 1 10.004 4zM9 13a3 3 0 1 0 6 0a3 3 0 1 0 -6 0",
	"cheque": "M0 0 M24 24 M11 14h2a2 2 0 0 0 0-4h-3c-.6 0-1.1.2-1.4.6L3 16m14.45 13.39 5.05-4.694C20.196 8 21 6.85 21 5.75a2.75 2.75 0 0 0-4.797-1.837.276.276 0 0 1-.406 0A2.75 2.75 0 0 0 11 5.75c0 1.2.802 2.248 1.5 2.946L16 11.95m2 15 6 6m7 20 1.6-1.4c.3-.4.8-.6 1.4-.6h4c1.1 0 2.1-.4 2.8-1.2l4.6-4.4a1 1 0 0 0-2.75-2.91",
	"compass": "M0 0 M24 24 M2 12a10 10 0 1 0 20 0a10 10 0 1 0 -20 0m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z",
	"crop": "M0 0 M24 24 M6 2v14a2 2 0 0 0 2 2h14M18 22V8a2 2 0 0 0-2-2H2",
	"crown": "M0 0 M24 24 M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294zM5 21h14",
	"equal": "M0 0 M24 24 M5 9L19 9M5 15L19 15",
	"flask-conical": "M0 0 M24 24 M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08A2 2 0 0 0 10 8V2M6.453 15h11.094M8.5 2h7",
	"gavel": "M0 0 M24 24 m14 13-8.381 8.38a1 1 0 0 1-3.001-3l8.384-8.381m16 16 6-6m21.5 10.5-8-8m8 8 6-6m8.5 7.5 8 8",
	"git-fork": "M0 0 M24 24 M9 18a3 3 0 1 0 6 0a3 3 0 1 0 -6 0M3 6a3 3 0 1 0 6 0a3 3 0 1 0 -6 0M15 6a3 3 0 1 0 6 0a3 3 0 1 0 -6 0M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9M12 12v3",
	"glasses": "M0 0 M24 24 M2 15a4 4 0 1 0 8 0a4 4 0 1 0 -8 0M14 15a4 4 0 1 0 8 0a4 4 0 1 0 -8 0M14 15a2 2 0 0 0-2-2 2 2 0 0 0-2 2M2.5 13 5 7c.7-1.3 1.4-2 3-2M21.5 13 19 7c-.7-1.3-1.5-2-3-2",
	"graduation-cap": "M0 0 M24 24 M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0zM22 10v6M6 12.5V16a6 3 0 0 0 12 0v-3.5",
	"hand-coins": "M0 0 M24 24 M11 15h2a2 2 0 1 0 0-4h-3c-.6 0-1.1.2-1.4.6L3 17m7 21 1.6-1.4c.3-.4.8-.6 1.4-.6h4c1.1 0 2.1-.4 2.8-1.2l4.6-4.4a2 2 0 0 0-2.75-2.91l-4.2 3.9m2 16 6 6M13.1 9a2.9 2.9 0 1 0 5.8 0a2.9 2.9 0 1 0 -5.8 0M3 5a3 3 0 1 0 6 0a3 3 0 1 0 -6 0",
	"handshake": "M0 0 M24 24 m11 17 2 2a1 1 0 1 0 3-3m14 14 2.5 2.5a1 1 0 1 0 3-3l-3.88-3.88a3 3 0 0 0-4.24 0l-.88.88a1 1 0 1 1-3-3l2.81-2.81a5.79 5.79 0 0 1 7.06-.87l.47.28a2 2 0 0 0 1.42.25L21 4m21 3 1 11h-2M3 3 2 14l6.5 6.5a1 1 0 1 0 3-3M3 4h8",
	"hash": "M0 0 M24 24 M4 9L20 9M4 15L20 15M10 3L8 21M16 3L14 21",
	"heart": "M0 0 M24 24 M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5",
	"heart-pulse": "M0 0 M24 24 M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5M3.22 13H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27",
	"landmark": "M0 0 M24 24 M10 18v-7M11.119 2.205a2 2 0 0 1 1.762 0l7.84 3.846A.5.5 0 0 1 20.5 7h-17a.5.5 0 0 1-.22-.949zM14 18v-7M18 18v-7M3 22h18M6 18v-7",
	"layout-template": "M0 0 M24 24 M4 3h16a1 1 0 0 1 1 1v5a1 1 0 0 1 -1 1h-16a1 1 0 0 1 -1 -1v-5a1 1 0 0 1 1 -1ZM4 14h7a1 1 0 0 1 1 1v5a1 1 0 0 1 -1 1h-7a1 1 0 0 1 -1 -1v-5a1 1 0 0 1 1 -1ZM17 14h3a1 1 0 0 1 1 1v5a1 1 0 0 1 -1 1h-3a1 1 0 0 1 -1 -1v-5a1 1 0 0 1 1 -1Z",
	"leaf": "M0 0 M24 24 M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10ZM2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12",
	"lectern": "M0 0 M24 24 M16 12h3a2 2 0 0 0 1.902-1.38l1.056-3.333A1 1 0 0 0 21 6H3a1 1 0 0 0-.958 1.287l1.056 3.334A2 2 0 0 0 5 12h3M18 6V3a1 1 0 0 0-1-1h-3M9 10h6a1 1 0 0 1 1 1v10a1 1 0 0 1 -1 1h-6a1 1 0 0 1 -1 -1v-10a1 1 0 0 1 1 -1Z",
	"library": "M0 0 M24 24 m16 6 4 14M12 6v14M8 8v12M4 4v16",
	"link": "M0 0 M24 24 M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71",
	"megaphone": "M0 0 M24 24 M11 6a13 13 0 0 0 8.4-2.8A1 1 0 0 1 21 4v12a1 1 0 0 1-1.6.8A13 13 0 0 0 11 14H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2zM6 14a12 12 0 0 0 2.4 7.2 2 2 0 0 0 3.2-2.4A8 8 0 0 1 10 14M8 6v8",
	"message-square-quote": "M0 0 M24 24 M14 14a2 2 0 0 0 2-2V8h-2M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2zM8 14a2 2 0 0 0 2-2V8H8",
	"newspaper": "M0 0 M24 24 M15 18h-5M18 14h-8M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-4 0v-9a2 2 0 0 1 2-2h2M11 6h6a1 1 0 0 1 1 1v2a1 1 0 0 1 -1 1h-6a1 1 0 0 1 -1 -1v-2a1 1 0 0 1 1 -1Z",
	"paper": "M0 0 M24 24 M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2zM14 2v5a1 1 0 0 0 1 1h5M10 9H8M16 13H8M16 17H8",
	"person-cap": "M0 0 M24 24 M7 8a5 5 0 1 0 10 0a5 5 0 1 0 -10 0M20 21a8 8 0 0 0-16 0",
	"person-lectern": "M0 0 M24 24 M2 3h20M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3m7 21 5-5 5 5",
	"pie-chart": "M0 0 M24 24 M21 12c.552 0 1.005-.449.95-.998a10 10 0 0 0-8.953-8.951c-.55-.055-.998.398-.998.95v8a1 1 0 0 0 1 1zM21.21 15.89A10 10 0 1 1 8 2.83",
	"radio": "M0 0 M24 24 M16.247 7.761a6 6 0 0 1 0 8.478M19.075 4.933a10 10 0 0 1 0 14.134M4.925 19.067a10 10 0 0 1 0-14.134M7.753 16.239a6 6 0 0 1 0-8.478M10 12a2 2 0 1 0 4 0a2 2 0 1 0 -4 0",
	"resize-figure": "M0 0 M24 24 M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7M14 15H9v-5M16 3h5v5M21 3 9 15",
	"round-table": "M0 0 M24 24 M18 21a8 8 0 0 0-16 0M5 8a5 5 0 1 0 10 0a5 5 0 1 0 -10 0M22 20c0-3.37-2-6.5-4-8a5 5 0 0 0-.45-8.3",
	"ruler": "M0 0 M24 24 M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.41 2.41 0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0Zm14.5 12.5 2-2m11.5 9.5 2-2m8.5 6.5 2-2m17.5 15.5 2-2",
	"scale": "M0 0 M24 24 M12 3v18m19 8 3 8a5 5 0 0 1-6 0zV7M3 7h1a17 17 0 0 0 8-2 17 17 0 0 0 8 2h1m5 8 3 8a5 5 0 0 1-6 0zV7M7 21h10",
	"shield": "M0 0 M24 24 M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z",
	"shield-off": "M0 0 M24 24 m2 2 20 20M5 5a1 1 0 0 0-1 1v7c0 5 3.5 7.5 7.67 8.94a1 1 0 0 0 .67.01c2.35-.82 4.48-1.97 5.9-3.71M9.309 3.652A12.252 12.252 0 0 0 11.24 2.28a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1v7a9.784 9.784 0 0 1-.08 1.264",
	"sparkles": "M0 0 M24 24 M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594zM20 2v4M22 4h-4M2 20a2 2 0 1 0 4 0a2 2 0 1 0 -4 0",
	"swords": "M0 0 M24 24 M14.5 17.5L3 6L3 3L6 3L17.5 14.5M13 19L19 13M16 16L20 20M19 21L21 19M14.5 6.5L18 3L21 3L21 6L17.5 9.5M5 14L9 18M7 17L4 20M3 19L5 21",
	"trending-up": "M0 0 M24 24 M16 7h6v6m22 7-8.5 8.5-5-5L2 17",
	"unlock": "M0 0 M24 24 M5 11h14a2 2 0 0 1 2 2v7a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-7a2 2 0 0 1 2 -2ZM7 11V7a5 5 0 0 1 9.9-1",
	"user-check": "M0 0 M24 24 m16 11 2 2 4-4M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M5 7a4 4 0 1 0 8 0a4 4 0 1 0 -8 0",
	"user-x": "M0 0 M24 24 M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M5 7a4 4 0 1 0 8 0a4 4 0 1 0 -8 0M17 8L22 13M22 8L17 13",
	"users": "M0 0 M24 24 M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 3.128a4 4 0 0 1 0 7.744M22 21v-2a4 4 0 0 0-3-3.87M5 7a4 4 0 1 0 8 0a4 4 0 1 0 -8 0",
	"voorzittershamer": "M0 0 M24 24 m14 13-8.381 8.38a1 1 0 0 1-3.001-3l8.384-8.381m16 16 6-6m21.5 10.5-8-8m8 8 6-6m8.5 7.5 8 8",
	"wind": "M0 0 M24 24 M12.8 19.6A2 2 0 1 0 14 16H2M17.5 8a2.5 2.5 0 1 1 2 4H2M9.8 4.4A2 2 0 1 1 11 8H2",
	"workflow": "M0 0 M24 24 M5 3h4a2 2 0 0 1 2 2v4a2 2 0 0 1 -2 2h-4a2 2 0 0 1 -2 -2v-4a2 2 0 0 1 2 -2ZM7 11v4a2 2 0 0 0 2 2h4M15 13h4a2 2 0 0 1 2 2v4a2 2 0 0 1 -2 2h-4a2 2 0 0 1 -2 -2v-4a2 2 0 0 1 2 -2Z"
};

export interface PerspectiefStijl {
	key: string;
	naam: string;
	kleur: string;
	icoon: string;
	/** tagsleutel -> icoonnaam */
	tags: Record<string, string>;
}

export const PERSPECTIEVEN: PerspectiefStijl[] = [
	{
		"key": "filosofisch-argumentatietheoretisch",
		"naam": "Filosofisch & Argumentatietheoretisch",
		"kleur": "#B68235",
		"icoon": "library",
		"tags": {
			"Walton-Causaal": "workflow",
			"Walton-Consequentie": "trending-up",
			"Walton-Expertise": "graduation-cap",
			"Walton-Analogie": "arrow-left-right",
			"Walton-Regel": "gavel",
			"Drogreden-Ad-Hominem": "user-x",
			"Drogreden-Stropop": "wind",
			"Drogreden-Vals-Dilemma": "git-fork",
			"Drogreden-Ontduiken-Bewijslast": "shield-off",
			"Drogreden-Bespelen-Publiek": "megaphone",
			"Meta-Bevoegdheid": "scale",
			"Meta-Agenda-Tijdigheid": "calendar-clock",
			"Meta-Reikwijdte": "crop",
			"Meta-Vorm-Setting": "layout-template",
			"Meta-Deelnemers": "users"
		}
	},
	{
		"key": "communicatiewetenschappelijk-media",
		"naam": "Communicatiewetenschappelijk & Media",
		"kleur": "#4C7C7A",
		"icoon": "radio",
		"tags": {
			"Frame-Episodisch": "camera",
			"Frame-Thematisch": "bar-chart-2",
			"Frame-Conflict": "swords",
			"Frame-Economisch": "banknote",
			"Frame-Menselijk-Belang": "heart",
			"Frame-Moraliteit": "compass",
			"Frame-Verantwoordelijkheid": "user-check",
			"Arena-Parlement": "landmark",
			"Arena-Legacy-Media": "newspaper",
			"Arena-Social-Media": "hash",
			"Arena-Wetenschap": "flask-conical",
			"Actor-Politicus": "person-lectern",
			"Actor-Expert": "glasses",
			"Actor-NGO": "cheque",
			"Actor-Bedrijf": "building-2",
			"Actor-Burger": "person-cap"
		}
	},
	{
		"key": "politicologisch-sociaal-psychologisch",
		"naam": "Politicologisch & Sociaal-Psychologisch",
		"kleur": "#B15E4A",
		"icoon": "brain",
		"tags": {
			"Ideologie-GAL": "leaf",
			"Ideologie-TAN": "shield",
			"Ideologie-Links-Economisch": "hand-coins",
			"Ideologie-Rechts-Economisch": "briefcase",
			"Moraliteit-Zorg": "heart-pulse",
			"Moraliteit-Eerlijkheid": "equal",
			"Moraliteit-Proportionaliteit": "resize-figure",
			"Moraliteit-Loyaliteit": "handshake",
			"Moraliteit-Autoriteit": "crown",
			"Moraliteit-Zuiverheid": "sparkles",
			"Moraliteit-Vrijheid": "unlock"
		}
	},
	{
		"key": "methodologisch-contextueel",
		"naam": "Methodologisch & Contextueel",
		"kleur": "#6B8558",
		"icoon": "ruler",
		"tags": {
			"Bewijs-Statistisch": "pie-chart",
			"Bewijs-Anekdotisch": "message-square-quote",
			"Bewijs-Causaal": "link",
			"Bewijs-Expert": "badge-check",
			"Context-Vragenuur": "lectern",
			"Context-Commissie": "round-table",
			"Context-Plenair": "voorzittershamer",
			"Context-Tweeminutendebat": "paper"
		}
	}
];

/** Icoonnaam voor een tagsleutel, over alle perspectieven heen. */
export const TAG_ICOON: Record<string, string> = {
	"Walton-Causaal": "workflow",
	"Walton-Consequentie": "trending-up",
	"Walton-Expertise": "graduation-cap",
	"Walton-Analogie": "arrow-left-right",
	"Walton-Regel": "gavel",
	"Drogreden-Ad-Hominem": "user-x",
	"Drogreden-Stropop": "wind",
	"Drogreden-Vals-Dilemma": "git-fork",
	"Drogreden-Ontduiken-Bewijslast": "shield-off",
	"Drogreden-Bespelen-Publiek": "megaphone",
	"Meta-Bevoegdheid": "scale",
	"Meta-Agenda-Tijdigheid": "calendar-clock",
	"Meta-Reikwijdte": "crop",
	"Meta-Vorm-Setting": "layout-template",
	"Meta-Deelnemers": "users",
	"Frame-Episodisch": "camera",
	"Frame-Thematisch": "bar-chart-2",
	"Frame-Conflict": "swords",
	"Frame-Economisch": "banknote",
	"Frame-Menselijk-Belang": "heart",
	"Frame-Moraliteit": "compass",
	"Frame-Verantwoordelijkheid": "user-check",
	"Arena-Parlement": "landmark",
	"Arena-Legacy-Media": "newspaper",
	"Arena-Social-Media": "hash",
	"Arena-Wetenschap": "flask-conical",
	"Actor-Politicus": "person-lectern",
	"Actor-Expert": "glasses",
	"Actor-NGO": "cheque",
	"Actor-Bedrijf": "building-2",
	"Actor-Burger": "person-cap",
	"Ideologie-GAL": "leaf",
	"Ideologie-TAN": "shield",
	"Ideologie-Links-Economisch": "hand-coins",
	"Ideologie-Rechts-Economisch": "briefcase",
	"Moraliteit-Zorg": "heart-pulse",
	"Moraliteit-Eerlijkheid": "equal",
	"Moraliteit-Proportionaliteit": "resize-figure",
	"Moraliteit-Loyaliteit": "handshake",
	"Moraliteit-Autoriteit": "crown",
	"Moraliteit-Zuiverheid": "sparkles",
	"Moraliteit-Vrijheid": "unlock",
	"Bewijs-Statistisch": "pie-chart",
	"Bewijs-Anekdotisch": "message-square-quote",
	"Bewijs-Causaal": "link",
	"Bewijs-Expert": "badge-check",
	"Context-Vragenuur": "lectern",
	"Context-Commissie": "round-table",
	"Context-Plenair": "voorzittershamer",
	"Context-Tweeminutendebat": "paper"
};
