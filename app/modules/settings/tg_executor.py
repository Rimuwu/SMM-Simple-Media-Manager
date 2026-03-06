


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


# Настройка репостов (forward_to)
# data - {'forward_to': [client_key, ...]}
async def forward_to(card: Card,
                     client_key: str,
                     data: dict
                     ) -> tuple[bool, str]:
    forward_list = data.get('forward_to')
    only_main_message = data.get('only_main_message', True)

    if forward_list is None:
        return False, "Missing 'forward_to' in data"
    if not isinstance(forward_list, list):
        return False, "Invalid 'forward_to' value. Expected list"

    # Optionally validate client keys (best-effort)
    # We just store the list as-is; UI ensures only telegram clients are selectable
    await card.refresh()
    current_settings = await card.get_clients_settings(client_key=client_key)
    cur = current_settings[0].data if current_settings else {}
    cur.update({'forward_to': forward_list, 'only_main_message': only_main_message})

    await card.set_client_setting(client_key=client_key, data=cur,
                                  type='forward_to')

    return True, ""


avaibale_types = {
    'auto_pin': auto_pin,
    'forward_to': forward_to
}