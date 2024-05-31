import os
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
    # Objects (Artworks)
    objects = pd.read_csv(
        "data/objects.csv",
        usecols=[
            "objectid",
            "isvirtual",
            "parentid",
            "title",
            "displaydate",
            "beginyear",
            "endyear",
            "medium",
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
        "data/published_images.csv",
        usecols=["uuid", "depictstmsobjectid", "maxpixels", "viewtype"],
    )

    published_images = published_images[
        published_images["maxpixels"].isna()
        & (published_images["viewtype"] == "primary")
    ]

    # Constituents (Artists)
    constituents = pd.read_csv(
        "data/constituents.csv",
        usecols=["constituentid", "forwarddisplayname", "displaydate"],
    )

    # Objects(Artworks)/Constituents(Artists) Mapping
    objects_constituents = pd.read_csv(
        "data/objects_constituents.csv",
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
    artists = (
        artists.groupby("objectid")[["artist_display"]].agg("\n".join).reset_index()
    )

    df = pd.merge(
        objects, published_images, left_on="objectid", right_on="depictstmsobjectid"
    )
    df = pd.merge(df, artists, on="objectid", how="left")
    print(df.shape)

    df["url"] = "https://api.nga.gov/iiif/" + df["uuid"] + "/full/1686,/0/default.jpg"
    df["image_id"] = "NGA-" + df["uuid"]

    columns = [
        "title",
        "artist_display",
        "displaydate",
        "beginyear",
        "endyear",
        "medium",
        "image_id",
        "url",
    ]
    df_paintings = df[columns].rename(
        columns={
            "displaydate": "date_display",
            "beginyear": "date_start",
            "endyear": "date_end",
        }
    )
    df_paintings["medium"] = df_paintings["medium"].str.capitalize()
    df_paintings.to_csv("data/paintings.csv", index=False)
