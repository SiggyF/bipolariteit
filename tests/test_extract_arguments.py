"""Tests voor de validatie van door de LLM teruggegeven argumenten."""

import pytest

from pipeline.extract_arguments import _validate_argument

GELDIG = {
    "stance": "pro",
    "typology": "factual",
    "quote_text": "Er zijn te weinig opvangplekken, dus de keten loopt vast.",
}


def test_valid_argument_passes():
    _validate_argument(dict(GELDIG))


def test_unknown_stance_is_rejected():
    with pytest.raises(ValueError, match="ongeldige stance"):
        _validate_argument({**GELDIG, "stance": "voor"})


def test_ander_onderwerp_requires_the_subject_it_is_actually_about():
    # Zonder onderwerp is dit label net zo weinig zeggend als 'unclear' -- de hele
    # reden ervoor is zichtbaar maken wát het ruime ingest-criterium binnenhaalt.
    with pytest.raises(ValueError, match="ander_onderwerp"):
        _validate_argument({**GELDIG, "stance": "ander_onderwerp"})

    _validate_argument({**GELDIG, "stance": "ander_onderwerp", "ander_onderwerp": "arbeidsmigratie"})
