def individual_serial(mtodo) -> dict:
    return {
        "id": str(mtodo["_id"]),
        "title": (mtodo["title"]),
        "description": (mtodo["description"]),
        "priority": str(mtodo["priority"]),
        "complete": (mtodo["complete"]),
        "owner_id": str(mtodo["owner_id"]),
    }


def list_serial(mtodos) -> list:
    return [individual_serial(mtodo) for mtodo in mtodos]