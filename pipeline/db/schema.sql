-- Bipolariteit datamodel
-- Kernprincipe: "we listen and we don't judge" -- geen enkele tabel mag een
-- kolom bevatten die feitelijke juistheid van een claim/argument beoordeelt
-- (dus geen truth/correct/verified/is_valid kolommen).

CREATE TABLE topics (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('news_rss', 'tweede_kamer', 'npo_subtitle')),
    name TEXT NOT NULL,
    url TEXT,
    retrieved_at TEXT NOT NULL
);

-- Een document is een enkele bewerkbare eenheid tekst: een RSS-item,
-- een sprekerbeurt uit een Tweede Kamer Verslag, of een SRT-segment.
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    topic_id INTEGER REFERENCES topics(id),
    actor_id INTEGER REFERENCES actors(id), -- bekende spreker (bv. TK-segmentatie); NULL voor bronnen zonder vooraf bekende actor
    external_id TEXT,
    title TEXT,
    content TEXT, -- de gesegmenteerde tekst zelf (bv. één sprekerbeurt); input voor Stage 1 LLM-extractie
    published_at TEXT,
    raw_ref TEXT,
    url TEXT,
    video_url TEXT,
    activiteit_soort TEXT, -- VLOS <activiteit soort="..."> waarde (bv. "Plenair debat"); NULL indien onbekend/niet TK
    extraction_attempted_at TEXT, -- gezet zodra Stage 1 (extract_arguments.py) dit document verwerkt heeft, ook als dat 0 arguments opleverde
    extraction_prompt_version TEXT, -- hash van pipeline/prompts/extract_argument.md t.t.v. de laatste extractiepoging; NULL = vóór versionering bestond
    extraction_model TEXT, -- LLM-modelnaam (bv. "qwen/qwen3.6-27b") gebruikt bij de laatste extractiepoging; NULL = vóór dit veld bestond
    activiteit_aanvangstijd TEXT, -- VLOS <activiteit><aanvangstijd>: starttijd van het hele debat (activiteit-niveau, niet de sprekerbeurt); input voor de video_url/Debat Direct-matchheuristiek
    activiteit_eindtijd TEXT, -- VLOS <activiteit><eindtijd>: eindtijd van het hele debat, idem
    tweedekamer_activiteit_url TEXT, -- publieke, mens-leesbare tweedekamer.nl-detailpagina van de Activiteit (via Activiteit.Nummer, zie docs/tk-data-sources-overview.md sectie 11) -- i.t.t. `url`, dat de machine-leesbare OData resource-XML is; NULL voor Activiteit-soorten zonder detailpagina (bv. e-mailprocedures) of nog niet gebackfilld
    is_voorzitter_turn INTEGER NOT NULL DEFAULT 0, -- 1 als de omsluitende VLOS <activiteitdeel><titel> "voorzitter" bevat (bv. "Spreekbeurt - De voorzitter"): de spreker zit op dat moment voor, spreekt procedureel, niet als woordvoerder van hun fractie. Fractie in de brondata blijft ongewijzigd (bv. CDA voor Krul) -- dit is puur een rol-vlag, geen partij-override. Stage 1 slaat deze documenten over (zie extract_arguments.py).
    speaker_role_title TEXT, -- VLOS <spreker><functie>-tekst (bv. "minister van Landbouw, Visserij, Voedselzekerheid en Natuur"), alleen gevuld wanneer <spreker soort="..."> niet "Tweede Kamerlid" is (dus voor bewindspersonen: Minister/Staatssecretaris). Actors.party blijft voor deze sprekers vaak NULL (geen fractie tijdens het spreken als bewindspersoon, zie scripts/backfill_minister_party.py voor de partij-backfill via de TK Persoon-API waar traceerbaar) -- dit veld toont in elk geval de functie, ongeacht of de partij bekend is.
    debatdirect_id TEXT, -- GUID van de match in Debat Direct's zoek-API (pipeline/enrich_video_url.py), gelijk voor alle documenten van dezelfde activiteit. Nodig om `https://api.debatdirect.tweedekamer.nl/debates/{id}` te bevragen voor het ruwe HLS-manifest (video.vodUrl) t.b.v. ondertitel-sync (zie pipeline/fetch_subtitles.py, docs/tk-data-sources-overview.md 5b) -- zonder deze id zou dat een nieuwe zoekopdracht per debat kosten voor dezelfde uitkomst. NULL voor documenten van vóór dit veld bestond, ook als video_url al wel gevuld is.
    raw_video_url TEXT, -- het afspeelbare HLS-manifest (vod_url + start/end-params), opgehaald via de debat-detail-API en hier gepersisteerd zodat de frontend die ongedocumenteerde API niet zelf hoeft aan te roepen (zie pipeline/fetch_subtitles.py). Gelijk voor alle documenten van dezelfde debatdirect_id.
    raw_video_url_checked_at TEXT, -- ISO-tijdstip van de laatste succesvolle ophaal/verificatie van raw_video_url. Het manifest is ongedocumenteerd en al minstens 1x gemigreerd (docs/tk-data-sources-overview.md 5b) -- dit veld maakt een latere periodieke hercontrole mogelijk (welke URL's zijn het langst geleden geverifieerd), die hercontrole zelf bestaat nog niet.
    speaker_person_id TEXT, -- VLOS <spreker objectid="...">: TK-Persoon-GUID van de spreker in déze beurt. Byte-identiek aan debatdirect's events[].objectId (zie pipeline/fetch_debate_events.py, docs/tk-data-sources-overview.md 5f) -- koppelt een VLOS-sprekerbeurt aan het bijbehorende debatdirect-event voor exacte video-kalibratie. NULL voor documenten van vóór dit veld bestond.
    turn_type TEXT CHECK (turn_type IN ('woordvoerder', 'interrumpant')), -- lokale VLOS-tagnaam van het sprekerbeurt-element (zie find_speaking_turns()). Samen met is_voorzitter_turn bepaalt dit welk debatdirect-eventType bij deze beurt hoort: 'interrumpant' -> 'interrupter', 'woordvoerder' -> 'chairman' als is_voorzitter_turn=1 anders 'speaker' (voorzitterbeurten blijken in de events-API uitsluitend als 'chairman' voor te komen, nooit 'speaker' -- geverifieerd op c1663929-...). NULL voor documenten van vóór dit veld bestond.
    speaker_event_anchor_at TEXT, -- Tier-1-anker uit de debatdirect events-API (pipeline/match_argument_spans.py calibrate_debate) als absolute wall-clock ISO8601-tijd, i.p.v. published_at (VLOS-markeertijd). Gebruikt door _speaker_event_url (build_static_data.py e.a.) voor de externe "video op dit moment"-deep-link naar Debat Direct -- published_at bleek voor sommige beurten uren te kunnen afwijken van de werkelijke spreektijd (issue #148-vervolg), waardoor die link naar het begin van het debat sprong. NULL voor beurten zonder Tier-1-anker (geen events-cache, of geen matchend event binnen het venster) -- daar valt de deep-link terug op published_at.
    text_stats TEXT, -- JSON-blob met ruwe tekststatistieken van content (issue #155), bv. {"word_count":123,"sentence_count":8,"syllable_count":210,"long_word_count":19,"unique_word_count":95,"token_count":180}, berekend door pipeline/text_stats.py. Alleen ruwe tellingen, niet de afgeleide leesbaarheidsindices zelf (Flesch-Douma/LIX/TTR blijven pure functies over deze tellingen, zodat een latere formulewijziging nooit een her-backfill vergt). Eén JSON-kolom i.p.v. een losse kolom per metriek, zodat een nieuwe metriek nooit een schemawijziging vergt. Gevuld door ingest_tk.py bij nieuwe imports en met terugwerkende kracht via scripts/backfill_document_tekststatistieken.py. NULL voor documenten van vóór dit veld bestond, of voor voorzitterbeurten/lege content (zie backfill-filter).
    activiteit_nummer TEXT, -- VLOS <activiteit><parlisid> (bv. "2026A02765"), TK's eigen Activiteit-Nummer -- dezelfde waarde als besloten in tweedekamer_activiteit_url, maar direct bruikbaar als join-sleutel naar activiteit_dossiernummers zonder de URL te hoeven parsen (zie #183/#348). NULL voor documenten van vóór dit veld bestond.
    motie_dossiernummer TEXT -- Kamerstukdossier-nummer van de motie die in déze spreekbeurt wordt ingediend/aangehouden/ingetrokken/gewijzigd (VLOS <draadboekfragment soort="Motie ..."> direct kind van deze beurt, met <zaken><zaak><dossiernummer>). Tekst, geen integer -- kan een toevoeging dragen (bv. "36800-B"). Het enige dossier-signaal dat echt op spreekbeurt-niveau zit i.p.v. activiteit-breed -- maar dus alleen gevuld voor de kleine subset spreekbeurten die zelf een motie-actie zijn (zie granulariteits-analyse in #348); NULL voor de rest.
);

-- Kamerstukdossiers die ergens in een hele Activiteit (het hele debat) aan de
-- orde zijn (VLOS <activiteit>/.../<zaken><zaak><dossiernummer>, of de TK
-- OData Agendapunt->Zaak->Kamerstukdossier-route) -- many-to-many, want één
-- activiteit kan over meerdere dossiers gaan. Dekt de hele activiteit, niet
-- een losse spreekbeurt; documents.motie_dossiernummer hierboven is het enige
-- signaal dat wél op spreekbeurt-niveau zit, maar alleen voor motie-acties.
-- Zie #183/#348 voor de volledige granulariteits-analyse.
CREATE TABLE activiteit_dossiernummers (
    activiteit_nummer TEXT NOT NULL,
    dossiernummer TEXT NOT NULL, -- geen integer -- kan een toevoeging dragen (bv. "36800-B")
    PRIMARY KEY (activiteit_nummer, dossiernummer)
);

-- Eenmalige, volledige kopie van de TK OData Kamerstukdossier-collectie
-- (7825 records in totaal op 2026-09-27, dus in zijn geheel op te halen in
-- ~32 gepagineerde calls -- zie scripts/db/fetch_kamerstukdossiers.py -- i.p.v.
-- losse lookups per dossiernummer). dossiernummer is dezelfde tekstvorm als
-- hierboven ("{Nummer}" of "{Nummer}-{Toevoeging}", bv. "36800-B"), zodat
-- documents.motie_dossiernummer en activiteit_dossiernummers.dossiernummer er
-- direct op kunnen joinen. Zie #183/#348.
CREATE TABLE kamerstukdossiers (
    dossiernummer TEXT PRIMARY KEY,
    nummer INTEGER NOT NULL,
    toevoeging TEXT,
    titel TEXT,
    afgesloten INTEGER
);

CREATE TABLE actors (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('person', 'party', 'organization')),
    party TEXT
);

-- Een argument is altijd toegeschreven aan een actor en een topic.
-- Bewust GEEN kolom voor waarheid/juistheid/verificatie.
CREATE TABLE arguments (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    actor_id INTEGER NOT NULL REFERENCES actors(id),
    stance TEXT NOT NULL CHECK (stance IN ('pro', 'contra', 'unclear', 'ander_onderwerp')),
    typology TEXT NOT NULL CHECK (typology IN ('factual', 'moral', 'economic', 'legal', 'other')),
    quote_text TEXT NOT NULL,
    quote_context TEXT,
    extracted_at TEXT NOT NULL,
    cluster_id INTEGER, -- hook voor toekomstige cross-source clustering; nog niet gevuld
    redactie_status TEXT CHECK (redactie_status IN ('balanced', 'imbalanced', 'flag')),
    tagged_at TEXT, -- gezet zodra de tag_arguments.py-pass voor dit argument compleet is (ook als dat 0 tags opleverde)
    prompt_version TEXT, -- hash van pipeline/prompts/extract_argument.md die dit specifieke argument opleverde; NULL = vóór versionering bestond
    extraction_model TEXT, -- LLM-modelnaam (bv. "qwen/qwen3.6-27b") die dit argument opleverde; NULL = vóór dit veld bestond
    tag_prompt_version TEXT, -- hash van pipeline/prompts/tag_argument.md t.t.v. de laatste tag_arguments.py-pass voor dit argument
    tag_model TEXT, -- LLM-modelnaam gebruikt door de tag_arguments.py-pass; NULL voor argumenten zonder LLM-tags of vóór dit veld bestond
    ander_onderwerp TEXT, -- alleen gevuld bij stance = 'ander_onderwerp': waar het argument dan wél over gaat (bv. "arbeidsmigratie", "ICT-migratie"). Zulke argumenten vallen buiten de pro/contra-as en dus buiten de export; dit veld maakt zichtbaar wát het ruime net binnenhaalt, in plaats van het in 'unclear' te laten verdwijnen.
    stijl_tagged_at TEXT, -- gezet zodra de losse Stijlmiddelen-backfill (scripts/agy_run_stijlmiddelen_backfill.py) voor dit argument compleet is, ook als dat 0 stijltags opleverde. Los van tagged_at omdat dit een aparte, smalle na-de-feiten-pass is voor argumenten die al vóór labelgroep "Stijlmiddelen" bestond volledig getagd waren.
    start_seconds REAL, -- seconden sinds videobegin waarop de quote start (zie pipeline/match_argument_spans.py, docs/design/videoplayer/README.md "Spannes verrijken"). Bij voorkeur zin-precies via WebVTT-ondertitel-matching, gekalibreerd op een exact per-beurt-anker uit de debatdirect events-API (docs/tk-data-sources-overview.md 5f); zonder VTT-match binnen een geankerde beurt valt dit terug op het beurt-anker zelf plus een spreektempo-schatting van de duur. NULL alleen als geen van beide lukt (bv. debat zonder ondertitels én zonder events-anker).
    end_seconds REAL -- idem, einde van de quote. Samen met start_seconds altijd als paar gevuld (nooit één van de twee NULL).
);

-- Genoemde getallen/claims en de bron die de spreker eraan toeschrijft.
-- Bewust GEEN is_correct kolom: we registreren alleen wat genoemd is en
-- welke bron ervoor wordt aangehaald, niet of het klopt.
CREATE TABLE claims (
    id INTEGER PRIMARY KEY,
    argument_id INTEGER NOT NULL REFERENCES arguments(id),
    claim_text TEXT NOT NULL,
    attributed_source_text TEXT
);

CREATE INDEX idx_documents_topic ON documents(topic_id);
-- document_exists() (ingest_tk.py, elke ingest-run) en alle scripts/backfill_*.py
-- zoeken op external_id; zonder index is dat een full table scan (191k+ rijen,
-- gemeten ~55ms per lookup) -- bij tienduizenden sprekerbeurten per backfill/ingest
-- was dit de eigenlijke bottleneck achter #145, niet de XML-parse zelf.
CREATE INDEX IF NOT EXISTS idx_documents_external_id ON documents(external_id);
CREATE INDEX idx_arguments_topic_stance ON arguments(topic_id, stance);
CREATE INDEX idx_arguments_document ON arguments(document_id);
CREATE INDEX idx_claims_argument ON claims(argument_id);

-- Argument-taxonomie van een argumentatie-onderzoeker (config/tags.toml), geladen
-- via pipeline/db/seed_tags.py. `active` is een soft-delete-vlag: elke seed-run
-- zet eerst alles inactief en activeert vervolgens alles wat nog in tags.toml
-- staat, zodat verwijderde/hernoemde tags stil worden zonder argument_tags-
-- geschiedenis te breken (FK's blijven geldig; nooit hard delete).
CREATE TABLE IF NOT EXISTS labelgroepen (
    naam TEXT PRIMARY KEY,
    perspectief TEXT NOT NULL,
    beschrijving TEXT NOT NULL,
    selectie TEXT NOT NULL CHECK (selectie IN ('enkel', 'meervoud')),
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS tags (
    sleutel TEXT PRIMARY KEY,
    labelgroep TEXT NOT NULL REFERENCES labelgroepen(naam),
    beschrijving TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_tags_labelgroep ON tags(labelgroep);

-- Many-to-many koppeling tussen arguments en tags. Bewust GEEN
-- juistheids-/waarheidskolom (zelfde principe als de rest van dit schema).
CREATE TABLE IF NOT EXISTS argument_tags (
    id INTEGER PRIMARY KEY,
    argument_id INTEGER NOT NULL REFERENCES arguments(id),
    tag_sleutel TEXT NOT NULL REFERENCES tags(sleutel),
    created_by TEXT NOT NULL CHECK (created_by IN ('llm', 'derived', 'manual')),
    confidence REAL,
    reden TEXT, -- korte, argument-specifieke onderbouwing waarom deze tag hier toegekend is (niet de generieke tag-beschrijving); NULL voor tags toegekend vóór dit veld bestond
    quote_fragment TEXT, -- verbatim, aaneengesloten stukje van arguments.quote_text waarop DEZE tag specifiek slaat (door het LLM zelf gekozen, zie pipeline/prompts/tag_argument.md). NULL heeft drie mogelijke betekenissen -- zie quote_fragment_status hieronder om ze te onderscheiden.
    quote_fragment_status TEXT CHECK (quote_fragment_status IN ('fragment', 'hele_quote', 'niet_herbeoordeeld')), -- onderscheidt drie betekenissen van quote_fragment IS NULL: 'hele_quote' = het LLM heeft déze tag in déze pass expliciet beoordeeld en de tag slaat op de hele quote (geen fragment van toepassing); 'niet_herbeoordeeld' = de tag bestond al vóór een latere --backfill-quote-fragment-pass over dit argument, maar die pass stelde deze specifieke tag_sleutel niet opnieuw voor (bv. het model koos ditmaal een andere sleutel binnen dezelfde labelgroep) -- er is dus geen fragmentoordeel over déze rij, in tegenstelling tot 'hele_quote'; NULL = nooit door enige quote_fragment-bewuste pass aangeraakt, meestal omdat de tag toegekend is vóór quote_fragment bestond (issue #109). 'fragment' betekent quote_fragment is gevuld (redundant met "quote_fragment IS NOT NULL", maar expliciet zodat een query niet zelf hoeft te herleiden welke van de betekenissen van NULL bedoeld is). Alleen relevant voor created_by='llm' (derived/manual-tags hebben geen quote_fragment-concept).
    start_seconds REAL, -- seconden sinds videobegin waarop quote_fragment start (zie pipeline/match_tag_spans.py), analoog aan arguments.start_seconds maar een niveau dieper. Nooit door het LLM gezet, alleen door die matching-pass. NULL als quote_fragment ontbreekt of niet matchte binnen de argument-spanne.
    end_seconds REAL, -- idem, einde van quote_fragment. Samen met start_seconds altijd als paar gevuld (nooit één van de twee NULL).
    assigned_at TEXT NOT NULL,
    UNIQUE (argument_id, tag_sleutel)
);
CREATE INDEX IF NOT EXISTS idx_argument_tags_argument ON argument_tags(argument_id);
CREATE INDEX IF NOT EXISTS idx_argument_tags_tag ON argument_tags(tag_sleutel);

-- Eén rij per LLM-call in extract_arguments.py/tag_arguments.py/redactie_check.py:
-- welk model, hoe lang de call duurde, en of hij slaagde. Bewust GEEN volledige
-- prompt-tekst hier -- het template staat al versiebeheerd in pipeline/prompts/
-- (prompt_version is er de hash van), en het ingevulde deel is voor extraction/
-- tagging gewoon wat al in documents/arguments staat. Dat nogmaals opslaan zou
-- deze tabel nodeloos laten groeien; de prompt wordt pas gereconstrueerd op het
-- moment dat hij getoond moet worden (zie pipeline/build_static_data.py).
CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY,
    stage TEXT NOT NULL CHECK (stage IN ('extraction', 'tagging', 'redactie')),
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    document_id INTEGER REFERENCES documents(id),
    argument_id INTEGER REFERENCES arguments(id),
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_vars TEXT, -- klein JSON-blok met invulwaarden die niet via document_id/argument_id terug te vinden zijn; alleen gebruikt door stage='redactie' (de willekeurige steekproef tegenargument-kandidaten, zie redactie_check.py:fetch_opposition_candidates), NULL voor extraction/tagging
    response TEXT,
    status TEXT NOT NULL CHECK (status IN ('ok', 'error')),
    error_message TEXT,
    started_at TEXT NOT NULL,
    duration_s REAL NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    reasoning_tokens INTEGER
);
CREATE INDEX IF NOT EXISTS idx_llm_calls_topic_model ON llm_calls(topic_id, model);
CREATE INDEX IF NOT EXISTS idx_llm_calls_stage ON llm_calls(stage);
-- Voor de "is dit argument al gecheckt?"-lookup in pipeline/tag_single.py
-- (NOT EXISTS tegen argument_id+stage+prompt_version+status) -- zonder deze
-- index is dat een correlated subquery-scan van heel llm_calls per kandidaat.
CREATE INDEX IF NOT EXISTS idx_llm_calls_argument_prompt ON llm_calls(argument_id, stage, prompt_version, status);
