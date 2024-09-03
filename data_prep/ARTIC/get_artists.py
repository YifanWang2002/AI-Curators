import re
import requests
import pandas as pd
import numpy as np
from time import sleep


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
    df_artworks = pd.read_csv("data/artworks.csv")
    print(df_artworks.info())

    nationality_white_list = pd.read_csv("data/nationality_white_list.csv")

    # Convert the DataFrame columns to lists
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

    # Save the result to CSV
    df_artists.to_csv("data/artists.csv", index=False)
