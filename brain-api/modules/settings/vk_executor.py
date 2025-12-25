

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
    # Обновляем настройку через ClientSetting модель
    current_settings = await card.get_clients_settings(client_key=client_key)
    cur = current_settings[0].data if current_settings else {}
    cur.update({'image_view': data['type']})

    await card.set_client_setting(client_key=client_key, data=cur,
                                  type='image_view'
                                  )

    return True, ""


avaibale_types = {
    "image_view": image_view,
}