import requests
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pprint import pprint


def format_display_name(row):
    return (
        f'{row["display_name"]} '
        + f'({"" if pd.isna(row["country_of_citizenship"]) else row["country_of_citizenship"]}, '
        + f'{"" if pd.isna(row["birth_year"]) else int(row["birth_year"])}-'
        + f'{"" if pd.isna(row["death_year"]) else int(row["death_year"])})'
    )


def search_wikidata(artist_name):  # return at most 3 search results
    search_url = f"https://www.wikidata.org/w/api.php?action=query&list=search&srsearch={artist_name}&srlimit=3&format=json"
    response = requests.get(search_url)
    return response.json().get("query", {}).get("search", [])


def process_wikipedia_page(page_title):
    # Directly get the extract (intro) for the Wikipedia page
    wikipedia_api_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&titles={page_title}&exintro=true&explaintext=true&format=json"
    response = requests.get(wikipedia_api_url).json()
    pages = response.get("query", {}).get("pages", {})
    page_data = next(
        iter(pages.values())
    )  # Get the first page in the "pages" dictionary
    biography = page_data.get("extract", "")
    return biography


def get_wikidata(artist_id):
    wikidata_url = f"https://www.wikidata.org/wiki/Special:EntityData/{artist_id}.json"
    data = requests.get(wikidata_url).json().get("entities", {}).get(artist_id, {})
    wikidata_title = data.get("labels", {}).get("en", {}).get("value", None)
    wikipedia_title = data.get("sitelinks", {}).get("enwiki", {}).get("title", None)
    return data, wikidata_title, wikipedia_title


# Function to check if a person is an artist based on Wikidata claims
def is_artist(claims):
    occupations = claims.get("P106", [])
    for occupation in occupations:
        occupation_id = occupation["mainsnak"]["datavalue"]["value"]["id"]
        if occupation_id in ["Q1028181", "Q483501"]:  # painter, artist
            return True
    return False


def is_human(claims):
    instance_of = claims.get("P31", [])
    for instance in instance_of:
        instance_id = instance["mainsnak"]["datavalue"]["value"]["id"]
        if instance_id == "Q5":  # human
            return True
    return False


# # (Given or Family names are missing for some artists)
# def get_given_and_family_names(claims):
#     def fetch_name(name_id):
#         if name_id:
#             url = f"https://www.wikidata.org/wiki/Special:EntityData/{name_id}.json"
#             data = requests.get(url).json()
#             labels = data["entities"][name_id]["labels"]

#             # Try to fetch the 'en' label, if not available, fall back to 'mul'
#             if "en" in labels:
#                 return labels["en"]["value"]
#             elif "mul" in labels:
#                 return labels["mul"]["value"]
#             else:
#                 return None
#         return None

#     given_name_id = (
#         claims.get("P735", [{}])[0]
#         .get("mainsnak", {})
#         .get("datavalue", {})
#         .get("value", {})
#         .get("id")
#     )
#     family_name_id = (
#         claims.get("P734", [{}])[0]
#         .get("mainsnak", {})
#         .get("datavalue", {})
#         .get("value", {})
#         .get("id")
#     )

#     return fetch_name(given_name_id), fetch_name(family_name_id)


def get_birth_death_dates(claims):
    def format_date(wikidata_date, precision):
        if not wikidata_date or not precision:
            return np.nan, np.nan
        year = wikidata_date[1:5]
        if precision >= 9:  # Year precision
            return year, year
        elif precision == 8:  # Decade precision
            return year, f"{year[:3]}0s"
        elif precision == 7:  # Century precision
            return year, f"{(int(year) - 1) // 100 + 1}th century"
        return np.nan, np.nan

    def extract_date_info(claim_key):
        claim = (
            claims.get(claim_key, [{}])[0]
            .get("mainsnak", {})
            .get("datavalue", {})
            .get("value", {})
        )
        return claim.get("time"), claim.get("precision")

    birth_date_year, birth_date_precision = extract_date_info("P569")
    death_date_year, death_date_precision = extract_date_info("P570")

    return (
        format_date(birth_date_year, birth_date_precision),
        format_date(death_date_year, death_date_precision),
    )


# Function to get the country_of_citizenship from Wikidata claims
def get_country_of_citizenship(claims):
    country_id = (
        claims.get("P27", [{}])[0]
        .get("mainsnak", {})
        .get("datavalue", {})
        .get("value", {})
        .get("id", None)
    )
    if country_id is not None:
        country_of_citizenship_data = requests.get(
            f"https://www.wikidata.org/wiki/Special:EntityData/{country_id}.json"
        ).json()
        return (
            country_id,
            country_of_citizenship_data["entities"][country_id]["labels"]["en"][
                "value"
            ],
        )
    return None, None


# Function to get an image URL from Wikidata claims
def get_image_url(claims):
    image = (
        claims.get("P18", [{}])[0]
        .get("mainsnak", {})
        .get("datavalue", {})
        .get("value", None)
    )
    return (
        f"https://commons.wikimedia.org/wiki/Special:FilePath/{image}"
        if image
        else None
    )


def fetch_wiki_info(display_name):
    def search_and_process(name):
        search_results = search_wikidata(name)

        # print(search_results)
        res = {
            "display_name": display_name,
            "name": None,
            "artist_id": None,
            # "given_name": None,
            # "family_name": None,
            "birth_date": None,
            "death_date": None,
            "birth_date_year": None,
            "death_date_year": None,
            "country_id": None,
            "country_of_citizenship": None,
            "image_url": None,
            "wikipedia_title": None,
            "biography": None,
        }
        for i, result in enumerate(search_results):

            artist_id = result["title"]
            wikidata_entity, wikidata_title, wikipedia_title = get_wikidata(artist_id)
            claims = wikidata_entity.get("claims", {})

            if not is_human(claims):
                continue

            res.update(
                {
                    "name": wikidata_title,
                    "artist_id": artist_id,
                    # "given_name": get_given_and_family_names(claims)[0],
                    # "family_name": get_given_and_family_names(claims)[1],
                    "birth_date_year": get_birth_death_dates(claims)[0][0],
                    "death_date_year": get_birth_death_dates(claims)[1][0],
                    "birth_date": get_birth_death_dates(claims)[0][1],
                    "death_date": get_birth_death_dates(claims)[1][1],
                    "country_id": get_country_of_citizenship(claims)[0],
                    "country_of_citizenship": get_country_of_citizenship(claims)[1],
                    "image_url": get_image_url(claims),
                }
            )

            # If Wikipedia page exists, get page details
            if wikipedia_title:
                biography = process_wikipedia_page(wikipedia_title)
                res.update(
                    {
                        "wikipedia_title": wikipedia_title,
                        "biography": biography,
                    }
                )

            break

        return res

    # Try original name
    result = search_and_process(display_name)

    # If no valid artist found, retry without "(...)"
    if not result["artist_id"] and "(" in display_name:
        display_name_cleaned = display_name.split("(")[0].strip()
        result = search_and_process(display_name_cleaned)

    return pd.Series(result)


def parallel_fetch_wiki_info(display_names):
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(fetch_wiki_info, name): name for name in display_names
        }
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Error fetching data for {futures[future]}: {e}")
        return pd.DataFrame(results)


if __name__ == "__main__":

    df = pd.read_csv("../new_data/artwork_with_gpt.csv")
    print(df.shape)

    df = df[~df["display_name"].isna()]
    print(df.shape)

    df["display_name"] = df["display_name"].str.replace(
        r", date(s)? unknown|\(After.*?\)|Attributed to|School of|Workshop of",
        "",
        regex=True,
    )
    # NGA and MET artist names originally did not include country_of_citizenship or years
    df.loc[df["source"].isin(["NGA", "MET"]), "display_name"] = df[
        df["source"].isin(["NGA", "MET"])
    ].apply(format_display_name, axis=1)

    df_artists = (
        df[["display_name", "artist_family_name", "artist_given_name"]]
        .rename(
            columns={
                "artist_family_name": "family_name",
                "artist_given_name": "given_name",
            }
        )
        .drop_duplicates(subset=["display_name"])
    )
    print(df_artists.shape)
    all_display_names = df_artists["display_name"]

    is_unknown = df_artists["display_name"].str.contains(
        "unknown|unidentified|^(after|imitator|follower|studio|style|in the style|circle)",
        case=False,
        na=False,
    )
    df_artists_unknown = df_artists[is_unknown][["display_name"]]
    df_artists_unknown.to_csv("data/artists_unknown.csv", index=False)
    df_artists = df_artists[~is_unknown]
    print(df_artists.shape)

    df_wiki = parallel_fetch_wiki_info(df_artists["display_name"].tolist())
    df_artists = pd.merge(df_wiki, df_artists, on="display_name")
    print(len(df_artists["artist_id"].unique()))
    print(df_artists[~df_artists["name"].isna()].shape)
    print(df_artists[~df_artists["biography"].isna()].shape)

    df_artists = df_artists[~df_artists["artist_id"].isna()]
    # It's okay if some threads of fetching wiki info get errors. All unprocessed artists are recorded here.
    df_artists_unprocessed = all_display_names[
        ~all_display_names.isin(
            pd.concat([df_artists["display_name"], df_artists_unknown["display_name"]])
        )
    ]
    df_artists_unprocessed.to_csv("data/artists_unprocessed.csv", index=False)

    df = df[["artwork_id", "display_name"]]
    df = pd.merge(
        df, df_artists[["display_name", "artist_id"]], how="left", on="display_name"
    )
    df.to_csv("data/artwork_with_artist.csv", index=False)
    df_artists = df_artists.drop_duplicates(subset=["artist_id"]).drop(
        columns=["display_name"]
    )
    df_artists.to_csv("data/artists.csv", index=False)

    # Example usage
    # artist_info = fetch_wiki_info("John Constable (English, 1776–1837)")
    # artist_info = fetch_wiki_info("Xugu (Chinese, 1823-1896)")  # no page
    # artist_info = fetch_wiki_info("Alessandro Magnasco (Italian, 1667-1749)")
    # artist_info = fetch_wiki_info("Vincent Gogh")
    # artist_info = fetch_wiki_info("Pintoricchio (Italian, c. 1454–1513)")
    # print(artist_info)

    # pprint(artist_info)
    # TODO: artists with no page – gpt / regular expression
    # TODO: country_of_citizenship – merge with location, and get continent, country, coordinates, and flag
