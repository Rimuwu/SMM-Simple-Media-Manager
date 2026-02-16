
from fastapi import HTTPException


def validate_poll(data: dict) -> dict:
    """Validate and normalize poll data.

    Expected format:
    {
        'question': str,
        'options': [str, ...],
        optional fields: 'type' ('regular'|'quiz')
    }
    Returns normalized dict or raises HTTPException
    """
    if not isinstance(data, dict):
        raise HTTPException(status_code=410, detail='Invalid data for poll')

    question = data.get('question')
    options = data.get('options')

    if not question or not isinstance(question, str):
        raise HTTPException(status_code=411, detail="Poll must contain 'question' (str)")
    if not options or not isinstance(options, list) or len(options) < 2:
        raise HTTPException(status_code=412, detail="Poll must contain at least two 'options'")

    # Normalize options to strings and trim
    norm_opts = [str(o).strip() for o in options if str(o).strip()]
    if len(norm_opts) < 2:
        raise HTTPException(status_code=413, detail="Poll options must contain at least two non-empty strings")
    elif len(norm_opts) > 10:
        raise HTTPException(status_code=417, detail="Poll options cannot exceed 10 items")

    p_type = data.get('type', 'regular') if data.get('type') in ('regular', 'quiz') else 'regular'

    normalized = {
        'question': question.strip(),
        'options': norm_opts,
        'is_anonymous': True,
        'type': p_type,
        'name': question.strip()[:25],
        'allows_multiple_answers': data.get('allows_multiple_answers', False)
    }


    if p_type == 'quiz':
        correct = data.get('correct_option_id')
        if correct is None:
            raise HTTPException(status_code=414,
                                detail="Quiz poll must include 'correct_option_id' index")
        try:
            ci = int(correct)
        except Exception:
            raise HTTPException(status_code=415, 
                                detail="'correct_option_id' must be integer index")
        if ci < 0 or ci >= len(norm_opts):
            raise HTTPException(status_code=416, 
                                detail="'correct_option_id' index out of range")
        normalized['correct_option_id'] = ci
        if 'explanation' in data:
            explanation = str(data.get('explanation', '')).strip()
            if explanation:
                normalized['explanation'] = explanation

    return normalized


def validate_inline_keyboard(data: dict) -> dict:
    """Validate and normalize inline keyboard data.

    Expected format:
    {
        'buttons': [
            {'text': str, 'url': str, optional 'style': 'primary'|'success'|'danger'},
            ...
        ],
        optional: 'name': str
    }
    Returns normalized dict or raises HTTPException
    """
    if not isinstance(data, dict):
        raise HTTPException(status_code=420, detail='Invalid data for inline_keyboard')

    buttons = data.get('buttons')
    if not buttons or not isinstance(buttons, list) or len(buttons) < 1:
        raise HTTPException(status_code=421, detail="Inline keyboard must contain at least one 'button'")

    normalized_buttons = []
    for btn in buttons:
        if not isinstance(btn, dict):
            raise HTTPException(status_code=422, detail="Each button must be a dict")

        text = btn.get('text')
        url = btn.get('url')
        style = btn.get('style', None)

        if not text or not isinstance(text, str):
            raise HTTPException(status_code=423, detail="Button must contain 'text' (str)")
        if not url or not isinstance(url, str):
            raise HTTPException(status_code=424, detail="Button must contain 'url' (str)")

        text = text.strip()
        url = url.strip()

        if not text or not url:
            raise HTTPException(status_code=425, detail="Button text and url cannot be empty")

        if url is not None and not (url.startswith('http://') or url.startswith('https://')):
            raise HTTPException(status_code=427, detail="Button 'url' must start with http:// or https://")

        normalized_buttons.append({
            'text': text,
            'url': url,
            'style': style if style in ('primary', 'success', 'danger') else None
        })

    if len(normalized_buttons) > 12:
        raise HTTPException(status_code=426, detail="Inline keyboard cannot exceed 12 buttons")

    name = data.get('name', 'Клавиатура ссылок')
    if isinstance(name, str):
        name = name.strip()
    if not name:
        name = 'Клавиатура ссылок'

    return {
        'buttons': normalized_buttons,
        'name': name[:50]
    }


avaibale_entities = {
    'poll': validate_poll,
    'inline_keyboard': validate_inline_keyboard
}
