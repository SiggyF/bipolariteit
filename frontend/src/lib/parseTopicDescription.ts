// topics.description (pipeline/db, zie ook prompts/extract_argument.md) volgt in de
// praktijk een vaste vorm: een korte intro, dan "PRO = ..." en "CONTRA = ...", optioneel
// gevolgd door een neutraliteitsdisclaimer. Dat wordt hier herkend zodat de topic-pagina
// het gestructureerd kan tonen i.p.v. als kale lopende tekst. Topics zonder deze vorm
// (pro/contra ontbreekt) vallen terug op alleen `intro`.
//
// Let op: PRO en CONTRA staan niet altijd door een lege regel gescheiden (bv. abortus:
// "...vrouw zelf.\nCONTRA = ..." zonder blanco regel ertussen) -- daarom zoeken we de
// "PRO ="/"CONTRA ="-markers zelf op i.p.v. te vertrouwen op alinea-grenzen.

export interface ParsedTopicDescription {
	intro: string[];
	pro: string | null;
	contra: string | null;
	note: string | null;
}

function clean(text: string): string {
	return text.replace(/\s+/g, " ").trim();
}

function splitParagraphs(text: string): string[] {
	return text
		.split(/\n{2,}/)
		.map(clean)
		.filter(Boolean);
}

export function parseTopicDescription(description: string): ParsedTopicDescription {
	const proIndex = description.indexOf("PRO =");
	const contraIndex = description.indexOf("CONTRA =");

	if (proIndex === -1 || contraIndex === -1 || contraIndex < proIndex) {
		return { intro: splitParagraphs(description), pro: null, contra: null, note: null };
	}

	const intro = splitParagraphs(description.slice(0, proIndex));
	const pro = clean(description.slice(proIndex + "PRO =".length, contraIndex));

	// Alles na "CONTRA =" tot de eerste lege regel is de contra-tekst zelf; wat
	// daarna nog volgt (gescheiden door een lege regel) is de disclaimer, indien
	// aanwezig.
	const [contraRaw, ...noteParts] = description.slice(contraIndex + "CONTRA =".length).split(/\n{2,}/);
	const contra = clean(contraRaw ?? "");
	const note = noteParts.length > 0 ? clean(noteParts.join(" ")) : null;

	return { intro, pro, contra, note: note || null };
}
