import pandas as pd

def display_artist(name, role, displaydate):
    if role in ["artist", "painter"]:
        artist_display = name
    elif role == "related artist":
        artist_display = "Possibly " + name
    elif role == "artist after":
        artist_display = "After " + name
    else:
        artist_display = name + " (" + role + ")"

    if pd.isna(displaydate):
        return artist_display
    return artist_display + " (" + displaydate.replace(" - ", "-") + ")"

# Adjust file paths to match the actual paths for the data files
objects_path = "data/objects.csv"
published_images_path = "data/published_images.csv"
constituents_path = "data/constituents.csv"
objects_constituents_path = "data/objects_constituents.csv"
output_path = "data/paintings.csv"

# Objects (Artworks)
objects = pd.read_csv(
    objects_path,
    usecols=[
        "objectid",
        "locationid",
        "title",
        "beginyear",
        "endyear",
        "medium",
        "dimensions",
        "classification",
        "isvirtual",
        "parentid"
    ],
)

objects = objects[
    (
        objects["medium"].isin(
            [
                "oil on canvas",
                "oil on card mounted on paperboard",
                "oil on panel",
                "oil on wood",
                "tempera on poplar panel",
            ]
        )
    )
    & (objects["isvirtual"] == 0)
    & (objects["parentid"].isna())
]

# Images
published_images = pd.read_csv(
    published_images_path,
    usecols=["uuid", "depictstmsobjectid", "maxpixels", "viewtype"],
)

published_images = published_images[
    published_images["maxpixels"].isna()
    & (published_images["viewtype"] == "primary")
]

# Constituents (Artists)
constituents = pd.read_csv(
    constituents_path,
    usecols=["constituentid", "forwarddisplayname", "lastname", "displaydate", "beginyear", "endyear", "nationality", "wikidataid"],
)

# Objects(Artworks)/Constituents(Artists) Mapping
objects_constituents = pd.read_csv(
    objects_constituents_path,
    usecols=["objectid", "constituentid", "roletype", "role"],
)
objects_constituents = objects_constituents[
    objects_constituents["roletype"] == "artist"
]

artists = pd.merge(objects_constituents, constituents, on="constituentid")
artists["artist_display"] = artists.apply(
    lambda row: display_artist(
        row["forwarddisplayname"], row["role"], row["displaydate"]
    ),
    axis=1,
)
artists = artists.rename(columns={
    "beginyear": "artist_beginyear",
    "endyear": "artist_endyear"
})

# Merge all dataframes to include all required fields
df = pd.merge(
    objects, published_images, left_on="objectid", right_on="depictstmsobjectid"
)
df = pd.merge(df, artists, on="objectid", how="left")

df["url"] = "https://api.nga.gov/iiif/" + df["uuid"] + "/full/max/0/default.jpg"
df["image_id"] = "NGA-" + df["uuid"]

columns = [
    "objectid",
    "locationid",
    "title",
    "beginyear",
    "endyear",
    "medium",
    "dimensions",
    "classification",
    "constituentid",
    "forwarddisplayname",
    "lastname",
    "displaydate",
    "artist_beginyear",
    "artist_endyear",
    "nationality",
    "wikidataid",
    "roletype",
    "role",
    "uuid",
    "viewtype",
    "maxpixels",
    "depictstmsobjectid",
    "artist_display",
    "url",
    "image_id"
]

df_paintings = df[columns].rename(
    columns={
        "beginyear": "date_start",
        "endyear": "date_end",
    }
)
df_paintings["medium"] = df_paintings["medium"].str.capitalize()
df_paintings.to_csv(output_path, index=False)

df_paintings.head()
