import os
import json
import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm  

def modify_artist_display(artist_display):
    if "\n" in artist_display:
        return artist_display.replace("\n", " (").replace("\u2013", "-") + ")"
    return artist_display  

paintings = []
all_artworks = []

# Using tqdm to show progress
for filename in tqdm(os.listdir("artworks"), desc="Processing artworks"):
    file_path = os.path.join("artworks", filename)

    with open(file_path, "r") as file:
        data = json.load(file)

        if "artwork_type_title" in data:
            all_artworks.append({
                "artwork_type_title": data["artwork_type_title"],
                "is_public_domain": data.get("is_public_domain", False)
            })

        if data.get("is_public_domain") and data.get("artwork_type_title") == "Painting":
            artwork_info = {
                "title": data.get("title"),
                "artist_display": modify_artist_display(data.get("artist_display")),
                "date_display": data.get("date_display"),
                "date_start": data.get("date_start"),
                "date_end": data.get("date_end"),
                "medium_display": data.get("medium_display"),
                "artwork_type_title": data.get("artwork_type_title"),
                "artist_title": data.get("artist_title"),
                "place_of_origin": data.get("place_of_origin"),
                "description": data.get("description"),
                "short_description": data.get("short_description"),
                "dimensions": data.get("dimensions"),
                "image_id": "ARTIC-" + data.get("image_id") if data.get("image_id") else "",
                "url": f"https://www.artic.edu/iiif/2/{data.get('image_id')}/full/max/0/default.jpg",
            }
            paintings.append(artwork_info)

df_paintings = pd.DataFrame(paintings)
df_paintings.to_csv("data/paintings.csv", index=False)

df_artworks = pd.DataFrame(all_artworks)
artwork_type_frequencies = df_artworks.pivot_table(index='artwork_type_title', columns='is_public_domain', aggfunc='size', fill_value=0)
artwork_type_frequencies.columns = ['Not Public Domain', 'Public Domain']
artwork_type_frequencies.to_csv('data/all_artwork_type_frequencies.csv')

# Optionally, plotting the frequency distribution
fig, ax = plt.subplots(figsize=(12, 8))
artwork_type_frequencies.plot(kind='bar', stacked=True, ax=ax)
ax.set_title('Frequency Distribution of All Artwork Types by Public Domain Status')
ax.set_xlabel('Artwork Type')
ax.set_ylabel('Frequency')
plt.savefig('data/all_artwork_type_frequencies.png')
plt.close()