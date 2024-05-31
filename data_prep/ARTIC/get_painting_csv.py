import os
import json

import pandas as pd


def modify_artist_display(artist_display):
    if "\n" in artist_display:
        return artist_display.replace("\n", " (").replace("\u2013", "-") + ")"


paintings = []

for filename in os.listdir("artworks"):
    file_path = os.path.join("artworks", filename)

    with open(file_path, "r") as file:
        data = json.load(file)

        if (
            data.get("is_public_domain")
            and data.get("artwork_type_title") == "Painting"
        ):
            artwork_info = {
                "title": data.get("title"),
                "artist_display": modify_artist_display(data.get("artist_display")),
                "date_display": data.get("date_display"),
                "date_start": data.get("date_start"),
                "date_end": data.get("date_end"),
                "medium": data.get("medium_display"),
                "image_id": "ARTIC-" + data.get("image_id")
                if data.get("image_id")
                else "",
                "url": f"https://www.artic.edu/iiif/2/{data.get('image_id')}/full/1686,/0/default.jpg",
            }  # There are images with width smaller than 1686, but here we ignore them.
            paintings.append(artwork_info)

df_paintings = pd.DataFrame(paintings)
df_paintings.to_csv("data/paintings.csv", index=False)
