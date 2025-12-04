import json

BASE_PATH = '/json/'

def open_json_file(filepath):
    try:
        with open(BASE_PATH + filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {filepath}")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {}

def open_properties():
    return open_json_file('settings.json').get('properties', {})

def open_settings():
    return open_json_file('settings.json')

def open_clients():
    return open_json_file('clients.json')