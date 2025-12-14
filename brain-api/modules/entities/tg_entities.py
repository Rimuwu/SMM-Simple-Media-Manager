from typing import Tuple
from fastapi import HTTPException


def validate_poll(data: dict) -> dict:
    """Validate and normalize poll data.

    Expected format:
    {
        'question': str,
        'options': [str, ...],
        optional fields: 'is_anonymous' (bool), 'type' ('regular'|'quiz')
    }
    Returns normalized dict or raises HTTPException
    """
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail='Invalid data for poll')

    question = data.get('question')
    options = data.get('options')

    if not question or not isinstance(question, str):
        raise HTTPException(status_code=400, detail="Poll must contain 'question' (str)")
    if not options or not isinstance(options, list) or len(options) < 2:
        raise HTTPException(status_code=400, detail="Poll must contain at least two 'options'")

    # Normalize options to strings and trim
    norm_opts = [str(o).strip() for o in options if str(o).strip()]
    if len(norm_opts) < 2:
        raise HTTPException(status_code=400, detail="Poll options must contain at least two non-empty strings")

    is_anonymous = bool(data.get('is_anonymous', True))
    p_type = data.get('type', 'regular') if data.get('type') in ('regular', 'quiz') else 'regular'

    normalized = {
        'question': question.strip(),
        'options': norm_opts,
        'is_anonymous': is_anonymous,
        'type': p_type
    }

    # If quiz type - optional 'correct_option' index must be provided
    if p_type == 'quiz':
        correct = data.get('correct_option')
        if correct is None:
            raise HTTPException(status_code=400, detail="Quiz poll must include 'correct_option' index")
        try:
            ci = int(correct)
        except Exception:
            raise HTTPException(status_code=400, detail="'correct_option' must be integer index")
        if ci < 0 or ci >= len(norm_opts):
            raise HTTPException(status_code=400, detail="'correct_option' index out of range")
        normalized['correct_option'] = ci

    return normalized


avaibale_entities = {
    'poll': validate_poll
}
