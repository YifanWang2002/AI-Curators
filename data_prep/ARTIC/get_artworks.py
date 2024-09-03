import os
import json
import pandas as pd
from tqdm import tqdm


def modify_artist_display(artist_display):
    if "\n" in artist_display:
        return artist_display.replace("\n", " (").replace("\u2013", "-") + ")"
    return artist_display


if __name__ == "__main__":
    artworks = []
    # Using tqdm to show progress
    for filename in tqdm(os.listdir("artworks"), desc="Processing artworks"):
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
                    "creation_year_start": data.get("date_start"),
                    "creation_year_end": data.get("date_end"),
                    "medium_display": data.get("medium_display"),
                    "artwork_type_title": data.get("artwork_type_title"),
                    "artist_id": data.get("artist_id"),
                    # "artist_title": data.get("artist_title"),
                    "location": data.get("place_of_origin"),
                    "description": data.get("description"),
                    "short_description": data.get("short_description"),
                    "dimension": data.get("dimensions"),
                    "artwork_id": data.get("image_id"),
                    "full_image_url": f"https://www.artic.edu/iiif/2/{data.get('image_id')}/full/max/0/default.jpg",
                }
                artworks.append(artwork_info)

    df_artworks = pd.DataFrame(artworks)
    df_artworks.to_csv("data/artworks.csv", index=False)
