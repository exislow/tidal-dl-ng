from tidalapi import Track


def name_builder_artist(media: Track) -> str:
    return ", ".join(artist.name for artist in media.artists)


def name_builder_title(media: Track) -> str:
    return media.name


def name_builder_item(media: Track) -> str:
    return f"{name_builder_artist(media)} - {name_builder_title(media)}"
