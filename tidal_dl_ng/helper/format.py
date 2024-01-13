def is_xml(value: str) -> bool:
    result = False

    if value:
        if value.startswith("<?xml"):
            result = True

    return result


def is_json(value: str) -> bool:
    result = False

    if value:
        if value.startswith("{"):
            result = True

    return result
