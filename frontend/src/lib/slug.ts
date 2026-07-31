/** URL-segment voor een partij- of persoonsnaam ("GroenLinks-PvdA", "Henk
 * Vermeer"). Puur weergave/routering -- de brondata (en de filterwaarde,
 * die op de exacte naam matcht) blijft ongewijzigd. */
export function slugify(name: string): string {
	return name
		.normalize("NFD")
		.replace(/[\u0300-\u036f]/g, "") // combining diacritics (na normalize("NFD"))
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/^-+|-+$/g, "");
}
