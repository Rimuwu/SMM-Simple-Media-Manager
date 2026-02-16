


from models.Card import Card


# Настройка автозакрепа для Telegram
# data - {'enabled': True|False}
async def auto_pin(card: Card,
                   client_key: str,
                   data: dict
                   ) -> tuple[bool, str]:
    if 'enabled' not in data:
        return False, "Missing 'enabled' in data"

    enabled = data.get('enabled')
    if not isinstance(enabled, bool):
        return False, "Invalid 'enabled' value. Expected boolean"

    await card.refresh()
    current_settings = await card.get_clients_settings(client_key=client_key)
    cur = current_settings[0].data if current_settings else {}
    cur.update({'auto_pin': enabled})

    await card.set_client_setting(client_key=client_key, data=cur,
                                  type='auto_pin')

    return True, ""


avaibale_types = {
    'auto_pin': auto_pin
}