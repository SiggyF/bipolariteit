// Gedeeld tussen ShareMenu.astro (SiteNav) en ShareMenuButton.vue (inline in
// de videospeler-controlsrij, issue #244) -- platformlijst/URL-opbouw en de
// insluitcode-snippet op één plek, zodat ze niet uit elkaar kunnen lopen.

export interface SharePlatform {
	key: string;
	label: string;
	icon: string;
	buildUrl: (title: string, url: string) => string;
}

export const SHARE_PLATFORMS: SharePlatform[] = [
	{
		key: "x",
		label: "X",
		icon: `<path d="M4 4l16 16M20 4L4 20"/>`,
		buildUrl: (title, url) => `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}`,
	},
	{
		key: "linkedin",
		label: "LinkedIn",
		icon: `<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7.5 10.5v6M7.5 7.6v.1M11.5 16.5v-6M11.5 13c0-1.4 1-2.5 2.4-2.5s2.6 1 2.6 2.6v3.4"/>`,
		buildUrl: (_title, url) => `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
	},
	{
		key: "bluesky",
		label: "Bluesky",
		icon: `<path d="M3 5c0 6 4.5 10 9 14 4.5-4 9-8 9-14 0-2-1.6-3-3-2.2C16.5 3.9 13.5 7 12 10 10.5 7 7.5 3.9 6 2.8 4.6 2 3 3 3 5z"/>`,
		buildUrl: (title, url) => `https://bsky.app/intent/compose?text=${encodeURIComponent(title + " " + url)}`,
	},
	{
		key: "whatsapp",
		label: "WhatsApp",
		icon: `<path d="M21 11.5a8.4 8.4 0 01-12.5 7.3L3 20.5l1.8-5.3A8.4 8.4 0 1121 11.5z"/><path d="M8.8 9c.3 2.6 3.6 5.9 6.2 6.2l1.2-1.5 2 1c-.4 1.3-1.7 1.9-3 1.6-3-.7-6-3.7-6.7-6.7-.3-1.3.3-2.6 1.6-3l1 2z"/>`,
		buildUrl: (title, url) => `https://wa.me/?text=${encodeURIComponent(title + " " + url)}`,
	},
	{
		key: "facebook",
		label: "Facebook",
		icon: `<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M14.5 8h-1.2c-.9 0-1.3.5-1.3 1.4V21M9.8 12.5h4.6"/>`,
		buildUrl: (_title, url) => `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
	},
	{
		key: "email",
		label: "E-mail",
		icon: `<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6.5L12 13l8.5-6.5"/>`,
		buildUrl: (title, url) => `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(url)}`,
	},
];

export function buildEmbedSnippet(embedUrl: string): string {
	return `<iframe src="${embedUrl}" width="100%" height="600" style="border:0" loading="lazy" allowfullscreen></iframe>`;
}
