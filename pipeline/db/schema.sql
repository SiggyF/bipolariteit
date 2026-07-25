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
    activiteit_aanvangstijd TEXT, -- VLOS <activiteit><aanvangstijd>: starttijd van het hele debat (activiteit-niveau, niet de sprekerbeurt); input voor de video_url/Debat Direct-matchheuristiek
    activiteit_eindtijd TEXT -- VLOS <activiteit><eindtijd>: eindtijd van het hele debat, idem
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
    stance TEXT NOT NULL CHECK (stance IN ('pro', 'contra', 'unclear')),
    typology TEXT NOT NULL CHECK (typology IN ('factual', 'moral', 'economic', 'legal', 'other')),
    quote_text TEXT NOT NULL,
    quote_context TEXT,
    extracted_at TEXT NOT NULL,
    cluster_id INTEGER, -- hook voor toekomstige cross-source clustering; nog niet gevuld
    redactie_status TEXT CHECK (redactie_status IN ('balanced', 'imbalanced', 'flag')),
    tagged_at TEXT, -- gezet zodra de tag_arguments.py-pass voor dit argument compleet is (ook als dat 0 tags opleverde)
    prompt_version TEXT -- hash van pipeline/prompts/extract_argument.md die dit specifieke argument opleverde; NULL = vóór versionering bestond
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

CREATE TABLE argument_oppositions (
    id INTEGER PRIMARY KEY,
    argument_a_id INTEGER NOT NULL REFERENCES arguments(id),
    argument_b_id INTEGER NOT NULL REFERENCES arguments(id),
    relation_type TEXT NOT NULL CHECK (relation_type IN ('direct_rebuttal', 'thematic')),
    created_by TEXT NOT NULL CHECK (created_by IN ('llm', 'manual')),
    confidence REAL
);

-- Redactionele bias-balans-check, één rij per document: pass_status is een
-- corpus-brede, deterministische pro/contra-snapshot van het hele topic op
-- het moment dat dit document werd verwerkt (zie redactie_check.py) -- niet
-- een oordeel over dit ene document op zich (dat is hier bijna altijd één
-- sprekersbeurt van één Kamerlid, dus per-document "eenzijdig" zou triviaal
-- altijd waar zijn). Nooit een oordeel over of een argument feitelijk klopt.
CREATE TABLE redactie_reviews (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    pass_status TEXT NOT NULL CHECK (pass_status IN ('balanced', 'imbalanced', 'flag')),
    notes TEXT,
    reviewer_model TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_documents_topic ON documents(topic_id);
CREATE INDEX idx_arguments_topic_stance ON arguments(topic_id, stance);
CREATE INDEX idx_arguments_document ON arguments(document_id);
CREATE INDEX idx_claims_argument ON claims(argument_id);
CREATE INDEX idx_oppositions_a ON argument_oppositions(argument_a_id);
CREATE INDEX idx_oppositions_b ON argument_oppositions(argument_b_id);
CREATE INDEX idx_redactie_document ON redactie_reviews(document_id);

-- Argument-taxonomie van een argumentatie-onderzoeker (data/tags.toml), geladen
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
    assigned_at TEXT NOT NULL,
    UNIQUE (argument_id, tag_sleutel)
);
CREATE INDEX IF NOT EXISTS idx_argument_tags_argument ON argument_tags(argument_id);
CREATE INDEX IF NOT EXISTS idx_argument_tags_tag ON argument_tags(tag_sleutel);
