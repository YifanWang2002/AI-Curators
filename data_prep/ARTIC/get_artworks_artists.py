import os
import re
import json
import requests
import pandas as pd
import numpy as np
from tqdm import tqdm
from time import sleep


def modify_artist_display(artist_display):
    if "\n" in artist_display:
        return artist_display.replace("\n", " (").replace("\u2013", "-") + ")"
    return artist_display


def extract_nationality(artist_display):
    # Use regex to split on spaces, commas, and parentheses
    words = re.split(r"\W+", artist_display)

    for word in words:
        # Check if the word is in the adjectives list
        if word in adjectives:
            return word
        # Check if the word is in the nouns list and return corresponding adjective
        elif word in nouns:
            return adjectives[nouns.index(word)]

    print(artist_display)
    return None


def fetch_artist_info(artist_id):
    # Remove the 'ARTIC-' prefix to get the actual artist ID
    url = f"https://api.artic.edu/api/v1/artists/{artist_id}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()

        # Extract birth_date and death_date, keep the field empty if not found
        birth_year = data["data"].get("birth_date", np.nan)
        death_year = data["data"].get("death_date", np.nan)
        forward_display_name = data["data"].get("title", "")
        preferred_display_name = data["data"].get("sort_title", "")
        print(birth_year, death_year, forward_display_name, preferred_display_name)

        return birth_year, death_year, forward_display_name, preferred_display_name
    except:
        return np.nan, np.nan, "", ""
    finally:
        sleep(0.02)


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
                    "medium": data.get("medium_display"),
                    "classification": data.get("artwork_type_title"),
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
    df_artworks.drop_duplicates(subset=["artwork_id"], inplace=True)
    print(df_artworks.info())

    # Get Artist Table
    nationality_white_list = pd.read_csv("data/nationality_white_list.csv")
    adjectives = nationality_white_list["adjective"].tolist()
    nouns = nationality_white_list["noun"].tolist()

    df_artists = df_artworks[["artist_id"]].dropna().drop_duplicates(keep="first")

    # Fetch birth_year and death_year for each artist
    df_artists[
        ["birth_year", "death_year", "forward_display_name", "preferred_display_name"]
    ] = (
        df_artists["artist_id"]
        .astype(int)
        .apply(lambda x: pd.Series(fetch_artist_info(x)))
    )

    # For Artwork table, add the musuem prefix and save
    df_artworks["artwork_id"] = "ARTIC-" + df_artworks["artwork_id"]
    df_artworks["artist_id"] = df_artworks["artist_id"].apply(
        lambda x: f"ARTIC-{int(x)}" if pd.notna(x) else x
    )
    df_artworks.to_csv("data/artworks.csv", index=False)

    # For Artist table, add the musuem prefix and save
    df_artists["artist_id"] = "ARTIC-" + df_artists["artist_id"].astype(int).astype(str)
    df_artists.to_csv("data/artists.csv", index=False)
