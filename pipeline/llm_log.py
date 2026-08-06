"""
Gedeelde logging-helper voor `llm_calls`: één rij per LLM-call vanuit
extract_arguments.py/tag_arguments.py/redactie_check.py. Slaat bewust geen
volledige prompt-tekst op (zie pipeline/db/schema.sql), alleen de gegevens
om 'm later te reconstrueren (document_id/argument_id/prompt_version) plus
wat wél nodig is om de call te evalueren (model, duur, respons, status).
"""

import json


def record_llm_call(
    conn,
    *,
    stage,
    topic_id,
    model,
    prompt_version,
    started_at,
    duration_s,
    document_id=None,
    argument_id=None,
    prompt_vars=None,
    response=None,
    status="ok",
    error_message=None,
    usage=None,
):
    usage = usage or {}
    conn.execute(
        """INSERT INTO llm_calls
           (stage, topic_id, document_id, argument_id, model, prompt_version, prompt_vars,
            response, status, error_message, started_at, duration_s,
            prompt_tokens, completion_tokens, reasoning_tokens)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            stage,
            topic_id,
            document_id,
            argument_id,
            model,
            prompt_version,
            json.dumps(prompt_vars, ensure_ascii=False) if prompt_vars is not None else None,
            response,
            status,
            error_message,
            started_at,
            duration_s,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("completion_tokens_details", {}).get("reasoning_tokens"),
        ),
    )
    conn.commit()
