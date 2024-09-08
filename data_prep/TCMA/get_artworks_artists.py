import os
import re
import json
import requests
import pandas as pd
import numpy as np
from tqdm import tqdm
from time import sleep
import ast
import uuid

def safe_eval(x):
    try:
        # Convert string to actual list/dictionary
        return ast.literal_eval(x)
    except ValueError:
        # Return None or some default if conversion fails
        return None

# function to extract all relevant artist information
def extract_artists_info(creators):
    if not creators or not isinstance(creators, list) or not isinstance(creators[0], dict):
        return pd.Series([None, None, None, None, None])

    artist = creators[0]  # assuming you're only interested in the first creator

    artist_id = str(artist.get('id', None))
    artist_display = artist.get('description', None)
    birth_year = str(artist.get('birth_year', None))
    death_year = str(artist.get('death_year', None))

    # Extract nationality from artist_display if present
    nationality = None
    if artist_display and ' (' in artist_display:
        parts = artist_display.split(' (')
        nationality = parts[1].split(',')[0] if len(parts) > 1 and ',' in parts[1] else None

    return pd.Series([artist_id, artist_display, birth_year, death_year, nationality])

def validate_images_url(df):
    # Convert 'images' from string to dictionary using ast.literal_eval
    df['images'] = df['images'].apply(ast.literal_eval)
    
    # Extract the image URL (if 'print' key exists)
    df['full_image_url'] = df['images'].apply(lambda x: x['full']['url'] if 'print' in x else None)
    
    # Filter the DataFrame to keep only rows where 'full_image_url' is not null
    has_image_url_df = df[df['full_image_url'].notnull()]
    
    return has_image_url_df


if __name__ == "__main__":
    csv_file = 'data/tcma_raw.csv'
    tcma = pd.read_csv(csv_file)

    # drop duplicated artworks based on id
    tcma.drop_duplicates(subset=["id"], inplace=True)

    # drop rows without image urls, and add the "full_image_url" column
    tcma = validate_images_url(tcma)
    print(f"Number of artwork with URL: {len(tcma)}")

    ### Process Artist Info
    # ensure all entries are converted to lists of dictionaries
    tcma['creators'] = tcma['creators'].apply(lambda x: safe_eval(x) if isinstance(x, str) else x)

    # Apply the function to extract artist info 
    tcma[['artist_id', 'artist_display', 'birth_year', 'death_year', 'nationality']] = tcma['creators'].apply(extract_artists_info)

    ### Process Artwork Info
    tcma_mapping = {
        'id': 'artwork_id',
        'title': 'title',
        'creation_date_earliest': 'creation_year_start',
        'creation_date_latest': 'creation_year_end',
        'technique': 'medium',
        'type': 'classification',
        'dimensions': 'dimension'
    }

    # applying the renaming
    tcma = tcma.rename(columns=tcma_mapping)

    ### Assign prefix to artist_id and artwork_id
    tcma['artwork_id'] = [uuid.uuid4() for _ in range(len(tcma))]
    tcma['artwork_id'] = 'TCMA-' + tcma['artwork_id'].astype(str)
    tcma["artist_id"] = tcma["artist_id"].apply(
        lambda x: f"TCMA-{int(x)}" if pd.notna(x) else x
    )
    ### Get Artwork Table
    df_artworks = tcma[["title","creation_year_start","creation_year_end",
                        "medium","classification","dimension",
                        "artwork_id","full_image_url",
                        "artist_id","artist_display"]]
    df_artworks.to_csv("data/artworks.csv", index=False)

    ### Get Artist Table
    df_artists = tcma[["artist_id", "artist_display", "birth_year", "death_year", "nationality"]].dropna().drop_duplicates(keep="first")
    df_artists.rename(columns={"artist_display": "display_name"}, inplace=True)
    df_artists.to_csv("data/artists.csv", index=False)
