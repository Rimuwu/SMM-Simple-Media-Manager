"""
Module for sending and managing entities (polls, etc) in previews and messages
"""
from aiogram import Bot
from aiogram.types import InputPollOption
from modules.api_client import brain_api


async def send_poll_preview(
    bot: Bot,
    chat_id: int,
    entity_data: dict,
    reply_markup=None,
) -> dict:
    """
    Send poll preview to user
    
    Args:
        bot: Aiogram Bot instance
        chat_id: Chat ID to send poll
        entity_data: Poll data dict with question, options, type, etc
        client_key: Client identifier (e.g., 'tg_executor')
    
    Returns:
        {'success': bool, 'message_id': int|None, 'error': str|None}
    """
    try:
        question = entity_data.get('question', 'Poll')
        options = entity_data.get('options', [])
        is_anonymous = entity_data.get('is_anonymous', True)
        poll_type = entity_data.get('type', 'regular')
        allows_multiple = entity_data.get('allows_multiple_answers', False)
        correct_option_id = entity_data.get('correct_option_id')
        explanation = entity_data.get('explanation')
        
        # Validate
        if not question or len(options) < 2:
            return {
                'success': False,
                'message_id': None,
                'error': 'Invalid poll: need question and at least 2 options'
            }
        
        # Convert options to InputPollOption
        poll_options = [InputPollOption(text=opt) for opt in options]
        
        # Send poll
        message = await bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=poll_options,
            is_anonymous=is_anonymous,
            type=poll_type,
            allows_multiple_answers=allows_multiple,
            correct_option_id=correct_option_id if poll_type == 'quiz' else None,
            explanation=explanation if poll_type == 'quiz' and explanation else None,
            reply_markup=reply_markup
        )
        
        return {
            'success': True,
            'message_id': message.message_id,
            'error': None
        }
    
    except Exception as e:
        return {
            'success': False,
            'message_id': None,
            'error': str(e)[:100]
        }

async def get_entities_for_client(
    card_id: str,
    client_id: str
) -> dict:
    """
    Get all entities for a specific client
    
    Args:
        card_id: Card UUID
        client_id: Client identifier
    
    Returns:
        {'success': bool, 'entities': list, 'error': str|None}
    """
    try:
        resp, status = await brain_api.get(
            f'/card/entities?card_id={card_id}&client_id={client_id}'
        )
        
        if status == 200 and resp:
            entities = resp.get('entities', [])
            return {'success': True, 'entities': entities, 'error': None}
        else:
            return {'success': False, 'entities': [], 'error': f'API error {status}'}
    
    except Exception as e:
        return {'success': False, 'entities': [], 'error': str(e)[:100]}

