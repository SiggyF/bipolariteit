// GEGENEREERD -- niet met de hand aanpassen.
// Bron: config/tags.toml.
// Opnieuw maken: uv run python scripts/export_tags_taxonomy.py

export interface TaxonomieTag {
	sleutel: string;
	beschrijving: string;
}

export interface TaxonomieLabelgroep {
	naam: string;
	beschrijving: string;
	/** true voor Actor Type/Issue Arena/Parlementaire Context: automatisch
	 * toegekend, niet door het LLM -- draagt daarom geen onderscheidend
	 * signaal tussen partijen of personen (zie pipeline/taxonomy.py). */
	deterministic: boolean;
	tags: TaxonomieTag[];
}

export interface TaxonomiePerspectief {
	naam: string;
	beschrijving: string;
	labelgroepen: TaxonomieLabelgroep[];
}

export const TAXONOMIE: TaxonomiePerspectief[] = [
	{
		"naam": "Filosofisch & Argumentatietheoretisch",
		"beschrijving": "Legt de interne logica en de retorische vormgeving van het argument bloot, en toetst de dialectische zuiverheid van het debat.",
		"labelgroepen": [
			{
				"naam": "Redeneerschema",
				"beschrijving": "Gestoeld op de argumentatieschema's voor presumptief redeneren van Douglas Walton.",
				"deterministic": false,
				"tags": [
					{
						"sleutel": "Walton-Causaal",
						"beschrijving": "Argumentatie gebaseerd op een directe oorzaak-gevolgrelatie."
					},
					{
						"sleutel": "Walton-Consequentie",
						"beschrijving": "Het verdedigen of aanvallen van een standpunt op basis van de verwachte praktische (voordelige of nadelige) gevolgen."
					},
					{
						"sleutel": "Walton-Expertise",
						"beschrijving": "Het argument leunt op de autoriteit, bevindingen of de verklaring van een specialist of expert."
					},
					{
						"sleutel": "Walton-Analogie",
						"beschrijving": "Er wordt een vergelijking getrokken met een historische gebeurtenis, een andere specifieke casus of een precedent."
					},
					{
						"sleutel": "Walton-Regel",
						"beschrijving": "Het argument beroept zich op een reeds gevestigde wet, formele regel of breed geaccepteerde maatschappelijke norm."
					}
				]
			},
			{
				"naam": "Debatzetten",
				"beschrijving": "Identificeert veelvoorkomende tactische zetten in het debat.",
				"deterministic": false,
				"tags": [
					{
						"sleutel": "Debatzet-Persoon-Aanspreken",
						"beschrijving": "Persoonlijke aanval op de tegenstander (op de man spelen) in plaats van een inhoudelijke weerlegging."
					},
					{
						"sleutel": "Debatzet-Herformuleren",
						"beschrijving": "Het vertekenen of overdrijven van het standpunt van de opponent om dit makkelijker te kunnen aanvallen."
					},
					{
						"sleutel": "Debatzet-Keuze-Aanscherpen",
						"beschrijving": "Zwart-wit denken; de situatie voorstellen alsof er slechts twee uiterste, elkaar uitsluitende opties bestaan."
					},
					{
						"sleutel": "Debatzet-Bewijs-Vragen",
						"beschrijving": "Doen alsof een claim geen bewijs behoeft of de tegenstander dwingen het tegendeel te bewijzen."
					},
					{
						"sleutel": "Debatzet-Gevoelens-Verwoorden",
						"beschrijving": "Emotioneel argumenteren gericht op het oproepen van angst, woede of medelijden bij de toehoorder."
					}
				]
			},
			{
				"naam": "Stijlmiddelen",
				"beschrijving": "Vormelijke en retorische middelen in de presentatie van een argument; claimt geen redeneerfout en geen framing, uitsluitend de taalvorm.",
				"deterministic": false,
				"tags": [
					{
						"sleutel": "Stijl-Slogan",
						"beschrijving": "Beknopte, pakkende frase."
					},
					{
						"sleutel": "Stijl-Herhaling",
						"beschrijving": "Herhaling van hetzelfde woord of dezelfde woordgroep binnen het fragment, ter nadruk."
					},
					{
						"sleutel": "Stijl-Aangekondigde-Opsomming",
						"beschrijving": "Vooraf het aantal elementen aankondigen (twee, drie, vijf, ...), gevolgd door een opsomming van precies dat aantal."
					},
					{
						"sleutel": "Stijl-Antithese",
						"beschrijving": "Het naast elkaar plaatsen van twee tegengestelde begrippen of ideeën."
					},
					{
						"sleutel": "Stijl-Retorische-Vraag",
						"beschrijving": "Een vraag waarvan het antwoord al besloten ligt in de formulering zelf."
					}
				]
			},
			{
				"naam": "Metadiscussie",
				"beschrijving": "Classificeert uitingen die de lopende of voorafgaande discussie zelf tot onderwerp maken (metaniveau), ter afbakening van inhoudelijke uitingen over de materiële beleidskwestie (objectniveau).",
				"deterministic": false,
				"tags": [
					{
						"sleutel": "Meta-Bevoegdheid",
						"beschrijving": "Uitingen over het formele mandaat, de wettelijke of constitutionele autoriteit, of de institutionele taakverdeling om over de kwestie te beslissen."
					},
					{
						"sleutel": "Meta-Agenda-Tijdigheid",
						"beschrijving": "Uitingen over de chronologische geschiktheid, de prioriteitstelling of de urgentie van de discussie op dit specifieke moment."
					},
					{
						"sleutel": "Meta-Reikwijdte",
						"beschrijving": "Uitingen over de thematische grenzen van het debat, de toelaatbaarheid van specifieke beweringen, of de legitimiteit van bepaalde linguïstische framings."
					},
					{
						"sleutel": "Meta-Vorm-Setting",
						"beschrijving": "Uitingen over de formele procedure, de interactieve spelregels, het vergaderformat of de fysieke en institutionele context van de uitwisseling."
					},
					{
						"sleutel": "Meta-Deelnemers",
						"beschrijving": "Uitingen over de spreektijdregelingen, de aanwezigheidsplicht van specifieke actoren, of de legitieme toegang van sprekers tot de lopende interactie."
					}
				]
			}
		]
	},
	{
		"naam": "Communicatiewetenschappelijk & Media",
		"beschrijving": "Analyseert hoe de werkelijkheid journalistiek en strategisch wordt gekaderd en binnen welke arena de interactie plaatsvindt.",
		"labelgroepen": [
			{
				"naam": "Framing-Focus",
				"beschrijving": "De focus van de berichtgeving volgens het model van Shanto Iyengar.",
				"deterministic": false,
				"tags": [
					{
						"sleutel": "Frame-Episodisch",
						"beschrijving": "Inzoomen op een specifiek, individueel incident, persoonlijk verhaal of een concrete casus."
					},
					{
						"sleutel": "Frame-Thematisch",
						"beschrijving": "Het benaderen van de kwestie vanuit een breder maatschappelijk, statistisch of historisch kader."
					}
				]
			},
			{
				"naam": "Generieke Nieuwsframes",
				"beschrijving": "Klassieke journalistieke invalshoeken volgens Semetko & Valkenburg.",
				"deterministic": false,
				"tags": [
					{
						"sleutel": "Frame-Conflict",
						"beschrijving": "De nadruk ligt op de felle strijd of meningsverschillen tussen personen, partijen of groepen."
					},
					{
						"sleutel": "Frame-Economisch",
						"beschrijving": "De focus ligt op de financiële kosten, baten of budgettaire gevolgen van een kwestie."
					},
					{
						"sleutel": "Frame-Menselijk-Belang",
						"beschrijving": "De focus ligt op de menselijke kant, de emoties of het individuele leed (Human Interest)."
					},
					{
						"sleutel": "Frame-Moraliteit",
						"beschrijving": "Inbranding vanuit ethische plichten, spirituele of religieuze principes."
					},
					{
						"sleutel": "Frame-Verantwoordelijkheid",
						"beschrijving": "De nadruk ligt op de schuldvraag of de plicht tot het oplossen van het probleem."
					}
				]
			},
			{
				"naam": "Issue Arena",
				"beschrijving": "De fysieke of digitale sfeer waarin de communicatie en argumentatie plaatsvindt.",
				"deterministic": true,
				"tags": [
					{
						"sleutel": "Arena-Parlement",
						"beschrijving": "Debat of uitspraak afkomstig uit de Eerste of Tweede Kamer."
					},
					{
						"sleutel": "Arena-Legacy-Media",
						"beschrijving": "Opinie- en nieuwsberichten geoogst uit kranten, tv-programma's of talkshows."
					},
					{
						"sleutel": "Arena-Social-Media",
						"beschrijving": "Discussies en uitingen op platforms zoals X (Twitter), LinkedIn of Reddit."
					},
					{
						"sleutel": "Arena-Wetenschap",
						"beschrijving": "Formele publicaties, onderzoeken of adviezen van planbureaus en academische instanties."
					}
				]
			},
			{
				"naam": "Actor Type",
				"beschrijving": "De achtergrond en hoedanigheid van de zender die het argument inbrengt.",
				"deterministic": true,
				"tags": [
					{
						"sleutel": "Actor-Politicus",
						"beschrijving": "Een gekozen volksvertegenwoordiger, bewindspersoon of partijvertegenwoordiger."
					},
					{
						"sleutel": "Actor-Expert",
						"beschrijving": "Een wetenschapper, onderzoeker, hoogleraar of erkend specialist."
					},
					{
						"sleutel": "Actor-NGO",
						"beschrijving": "Een maatschappelijke belangenorganisatie, stichting of actiegroep."
					},
					{
						"sleutel": "Actor-Bedrijf",
						"beschrijving": "Vertegenwoordigers van het bedrijfsleven, de industrie of werkgeversorganisaties."
					},
					{
						"sleutel": "Actor-Burger",
						"beschrijving": "Een individuele burger, ervaringsdeskundige, columnist of briefschrijver."
					}
				]
			}
		]
	},
	{
		"naam": "Politicologisch & Sociaal-Psychologisch",
		"beschrijving": "Legt de onderliggende waarden, politieke breuklijnen en diepe morele overtuigingen bloot.",
		"labelgroepen": [
			{
				"naam": "Cultureel-Ideologische Breuklijn",
				"beschrijving": "Traditionele en moderne politieke dimensies in het Nederlandse politieke spectrum.",
				"deterministic": false,
				"tags": [
					{
						"sleutel": "Ideologie-GAL",
						"beschrijving": "Progressief, ecologisch, kosmopolitisch (Green, Alternative, Libertarian)."
					},
					{
						"sleutel": "Ideologie-TAN",
						"beschrijving": "Conservatief, traditioneel, nationalistisch (Traditional, Authoritarian, Nationalist)."
					},
					{
						"sleutel": "Ideologie-Links-Economisch",
						"beschrijving": "Gericht op herverdeling van welvaart, sterke collectieve voorzieningen en overheidsingrijpen."
					},
					{
						"sleutel": "Ideologie-Rechts-Economisch",
						"beschrijving": "Gericht op de vrije markt, deregulering en individuele verantwoordelijkheid."
					}
				]
			},
			{
				"naam": "Morele Fundamenten",
				"beschrijving": "De psychologische pijlers van morele oordeelsvorming (Moral Foundations Theory).",
				"deterministic": false,
				"tags": [
					{
						"sleutel": "Moraliteit-Zorg",
						"beschrijving": "Gericht op empathie, compassie en het voorkomen van leed en schade bij kwetsbaren."
					},
					{
						"sleutel": "Moraliteit-Eerlijkheid",
						"beschrijving": "Gericht op gelijke kansen, gelijke rechten en onpartijdige behandeling (equality)."
					},
					{
						"sleutel": "Moraliteit-Proportionaliteit",
						"beschrijving": "Gericht op rechtvaardigheid naar rato van inspanning; belonen naar werken en het straffen van profiteurs."
					},
					{
						"sleutel": "Moraliteit-Loyaliteit",
						"beschrijving": "Gericht op groeps-solidariteit, vaderlandsliefde en trouw aan de eigen gemeenschap (in-group)."
					},
					{
						"sleutel": "Moraliteit-Autoriteit",
						"beschrijving": "Gericht op respect voor traditie, legitieme hiërarchie, wetten en maatschappelijke orde."
					},
					{
						"sleutel": "Moraliteit-Zuiverheid",
						"beschrijving": "Gericht op het vermijden van morele of fysieke besmetting; streven naar het schone, natuurlijke of verhevene."
					},
					{
						"sleutel": "Moraliteit-Vrijheid",
						"beschrijving": "Gericht op individuele autonomie en weerstand tegen dwang of onderdrukking door dominante actoren."
					}
				]
			}
		]
	},
	{
		"naam": "Methodologisch & Contextueel",
		"beschrijving": "Beschrijft de empirische kwaliteit van de bewijsvoering en de formele institutionele context.",
		"labelgroepen": [
			{
				"naam": "Type Bewijsvoering",
				"beschrijving": "De empirische of logische onderbouwing die wordt gebruikt om de claim te staven.",
				"deterministic": false,
				"tags": [
					{
						"sleutel": "Bewijs-Statistisch",
						"beschrijving": "Onderbouwd met kwantitatieve gegevens, cijfers, percentages of grootschalig representatief onderzoek."
					},
					{
						"sleutel": "Bewijs-Anekdotisch",
						"beschrijving": "Onderbouwd met één specifiek praktijkgeval, incident, exemplar of persoonlijk verhaal."
					},
					{
						"sleutel": "Bewijs-Causaal",
						"beschrijving": "Onderbouwd met een heldere, mechanistische of logische verklaring van oorzaak en gevolg."
					},
					{
						"sleutel": "Bewijs-Expert",
						"beschrijving": "Onderbouwd met de consensus, verklaring of het oordeel van een erkend specialist."
					}
				]
			},
			{
				"naam": "Parlementaire Context",
				"beschrijving": "De specifieke debatvorm binnen de Tweede Kamer (indien de issue arena parlementair is).",
				"deterministic": true,
				"tags": [
					{
						"sleutel": "Context-Vragenuur",
						"beschrijving": "Mondeling vragenuur op dinsdag; zeer korte spreektijden en vaak gekenmerkt door felle confrontaties en soundbites."
					},
					{
						"sleutel": "Context-Commissie",
						"beschrijving": "Commissiedebat of wetgevingsoverleg; technisch en gedetailleerd van aard met een hogere argumentatieve kwaliteit."
					},
					{
						"sleutel": "Context-Plenair",
						"beschrijving": "Groot plenair debat in de plenaire zaal; sterk ideologisch van aard (bijv. de Algemene Politieke Beschouwingen)."
					},
					{
						"sleutel": "Context-Tweeminutendebat",
						"beschrijving": "Kort afrondend plenair debat (2 minuten spreektijd) dat uitsluitend bedoeld is om moties in te dienen."
					}
				]
			}
		]
	}
];
