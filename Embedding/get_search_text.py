import pandas as pd


df = pd.read_csv("data/paintings_v2.csv")


df["artist"] = df["artist_display"]
df["content"] = df[["overview", "main_objects", "other_objects"]].agg(" ".join, axis=1)
df["style"] = df[["style", "style_tags", "movement", "medium"]].agg(" ".join, axis=1)
df["theme"] = df[["theme", "theme_tags"]].agg(" ".join, axis=1)

df["overall"] = (
    df["title"]
    + ". "
    + df["date_display"]
    + ". "
    + df["artist_display"]
    + ". "
    + df[["intro", "content", "style", "theme"]].agg(" ".join, axis=1)
)


df["overall"] = "passage: " + df["overall"]
df[["overall"]].to_csv("data/search_e5.csv", index=False)
