def get_tidal_media_id(url_or_id_media: str) -> str:
    id_dirty = url_or_id_media.rsplit("/", 1)[-1]
    id = id_dirty.rsplit("?", 1)[0]

    return id


def get_tidal_media_type(url_media: str) -> str | bool:
    result = False
    url_split = url_media.split("/")[-2]

    if len(url_split) > 1:
        result = url_media.split("/")[-2]

    return result
