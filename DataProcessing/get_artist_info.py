import requests
from pprint import pprint


# Function to search Wikipedia for an artist
def search_wikipedia(artist_name):
    search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={artist_name}&format=json"
    print(f"Searching Wikipedia for: {artist_name}")
    response = requests.get(search_url)
    return response.json().get("query", {}).get("search", [])


# Function to get page properties from Wikipedia
def get_page_properties(page_id):
    pageprops_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageprops&pageids={page_id}&format=json"
    pageprops_response = requests.get(pageprops_url).json()
    page_props = (
        pageprops_response.get("query", {})
        .get("pages", {})
        .get(str(page_id), {})
        .get("pageprops", {})
    )
    return page_props.get("wikibase_item")


# Function to get data from Wikidata using a Wikibase item
def get_wikidata(wikibase_item):
    wikidata_url = (
        f"https://www.wikidata.org/wiki/Special:EntityData/{wikibase_item}.json"
    )
    return requests.get(wikidata_url).json().get("entities", {}).get(wikibase_item, {})


# Function to check if a person is an artist based on Wikidata claims
def is_artist(claims):
    occupations = claims.get("P106", [])
    for occupation in occupations:
        occupation_id = occupation["mainsnak"]["datavalue"]["value"]["id"]
        if occupation_id in ["Q1028181", "Q483501"]:  # painter, artist
            return True
    return False


def get_birth_death_dates(claims):
    birth_date = (
        claims.get("P569", [{}])[0]
        .get("mainsnak", {})
        .get("datavalue", {})
        .get("value", {})
        .get("time", "Unknown")
    )
    death_date = (
        claims.get("P570", [{}])[0]
        .get("mainsnak", {})
        .get("datavalue", {})
        .get("value", {})
        .get("time", "Unknown")
    )
    return birth_date, death_date


# Function to get the nationality from Wikidata claims
def get_nationality(claims):
    nationality_id = (
        claims.get("P27", [{}])[0]
        .get("mainsnak", {})
        .get("datavalue", {})
        .get("value", {})
        .get("id", "Unknown")
    )
    if nationality_id != "Unknown":
        nationality_data = requests.get(
            f"https://www.wikidata.org/wiki/Special:EntityData/{nationality_id}.json"
        ).json()
        return nationality_data["entities"][nationality_id]["labels"]["en"]["value"]
    return "Unknown"


# Function to get an image URL from Wikidata claims
def get_image_url(claims):
    image = (
        claims.get("P18", [{}])[0]
        .get("mainsnak", {})
        .get("datavalue", {})
        .get("value", "No image available.")
    )
    return (
        f"https://commons.wikimedia.org/wiki/Special:FilePath/{image}"
        if image != "No image available."
        else "No image available."
    )


# Main function to fetch artist data
def fetch_wikipedia_summary(artist_name):
    search_results = search_wikipedia(artist_name)

    print(f"Search results: {search_results[:3]}")

    for result in search_results[:3]:
        print()
        page_id = result["pageid"]
        title = result["title"]
        print(f"Checking page: {title} (ID: {page_id})")

        wikibase_item = get_page_properties(page_id)

        if wikibase_item:
            print(f"Found Wikibase item: {wikibase_item}")
            wikidata_entity = get_wikidata(wikibase_item)
            claims = wikidata_entity.get("claims", {})

            if not is_artist(claims):
                print(f"{title} is not an artist. Skipping.")
                continue

            birth_date, death_date = get_birth_death_dates(claims)
            nationality = get_nationality(claims)
            image_url = get_image_url(claims)

            res = {
                "title": title,
                "birth_date": birth_date,
                "death_date": death_date,
                "nationality": nationality,
                "image_url": image_url,
            }

            return res

    return "No page has been found"


# Example usage
artist_info = fetch_wikipedia_summary("John Constable (English, 1776–1837)")
pprint(artist_info)
