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


if __name__ == "__main__":
    # Inputs
    objects_path = "data/objects.csv"
    published_images_path = "data/published_images.csv"
    constituents_path = "data/constituents.csv"
    objects_constituents_path = "data/objects_constituents.csv"
    # Outputs
    artworks_path = "data/artworks.csv"
    artists_path = "data/artists.csv"

    # Objects (Artworks)
    objects = pd.read_csv(
        objects_path,
        usecols=[
            "objectid",
            "title",
            "beginyear",
            "endyear",
            "medium",
            "dimensions",
            "classification",
            "isvirtual",
            "parentid",
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
        usecols=[
            "constituentid",
            "preferreddisplayname",
            "forwarddisplayname",
            # "lastname",
            "displaydate",
            "beginyear",
            "endyear",
            "nationality",
            "wikidataid",
        ],
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
    artists = artists.rename(
        columns={"beginyear": "artist_beginyear", "endyear": "artist_endyear"}
    )

    # Merge all dataframes to include all required fields
    df = pd.merge(
        objects, published_images, left_on="objectid", right_on="depictstmsobjectid"
    )
    df = pd.merge(df, artists, on="objectid", how="left")

    df["full_image_url"] = (
        "https://api.nga.gov/iiif/" + df["uuid"] + "/full/max/0/default.jpg"
    )

    df_artworks = (
        df[
            [
                "title",
                "beginyear",
                "endyear",
                "medium",
                "classification",
                "dimensions",
                "uuid",
                "full_image_url",
                "artist_display",
                "constituentid",
            ]
        ]
        .rename(
            columns={
                "beginyear": "creation_year_start",
                "endyear": "creation_year_end",
                "dimensions": "dimension",
                "constituentid": "artist_id",
                "uuid": "artwork_id",
            }
        )
        .drop_duplicates(subset=["artwork_id"])
    )

    df_artworks["medium"] = df_artworks["medium"].str.capitalize()
    df_artworks["artwork_id"] = "NGA-" + df_artworks["artwork_id"]
    df_artworks["artist_id"] = "NGA-" + df_artworks["artist_id"].astype(str)
    df_artworks.to_csv(artworks_path, index=False)

    # Get Artist Table
    df_artists = (
        df[
            [
                "constituentid",
                "preferreddisplayname",
                "forwarddisplayname",
                "artist_beginyear",
                "artist_endyear",
                "nationality",
            ]
        ]
        .rename(
            columns={
                "constituentid": "artist_id",
                "preferreddisplayname": "preferred_display_name",
                "forwarddisplayname": "forward_display_name",
                "artist_beginyear": "birth_year",
                "artist_endyear": "death_year",
            }
        )
        .drop_duplicates(subset=["artist_id"])
    )
    df_artists["artist_id"] = "NGA-" + df_artists["artist_id"].astype(str)
    df_artists.to_csv(artists_path, index=False)
