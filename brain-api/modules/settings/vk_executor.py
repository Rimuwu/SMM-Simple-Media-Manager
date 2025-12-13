

from models.Card import Card


# single (1 для клиента)
# data - {'type': grid / carousel}
async def image_view(card: Card, 
                     client_key: str,
                     data: dict
                     ) -> tuple[bool, str]:
    
    if 'type' not in data:
        return False, "Missing 'type' in data"

    if data['type'] not in ['grid', 'carousel']:
        return False, "Invalid 'type' in data. Must be 'grid' or 'carousel'"

    await card.refresh()
    card.clients_settings[client_key][
        'image_view'
        ] = data['type']
    await card.save()

    return True, ""


avaibale_types = {
    "image_view": image_view,
}