

from typing import Any
from modules.json_get import open_properties

properties = open_properties() or {}

def properties_transform(
        property_name: str, 
        data: Any
    ) -> dict:

    transformed = {
        f'id_{properties[property_name]["id"]}': data
    }

    return transformed

def multi_properties(**kwargs) -> dict:
    result = {}

    for key, value in kwargs.items():
        transformed = properties_transform(key, value)
        result.update(transformed)
    return result
