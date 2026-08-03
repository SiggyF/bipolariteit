import { TAXONOMIE } from "./tagsTaxonomy.generated";

export { TAXONOMIE };

export interface TagMeta {
	sleutel: string;
	beschrijving: string;
	labelgroep: string;
	perspectief: string;
	deterministic: boolean;
}

/** Platte lijst van alle tags uit de taxonomie, voor getStaticPaths op /tags/[sleutel]. */
export const ALLE_TAGS: TagMeta[] = TAXONOMIE.flatMap((perspectief) =>
	perspectief.labelgroepen.flatMap((labelgroep) =>
		labelgroep.tags.map((tag) => ({
			sleutel: tag.sleutel,
			beschrijving: tag.beschrijving,
			labelgroep: labelgroep.naam,
			perspectief: perspectief.naam,
			deterministic: labelgroep.deterministic,
		})),
	),
);
