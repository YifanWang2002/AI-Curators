import requests
from location_types import location_types
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed


# Function to search Wikipedia for an artist or location
def search_wikipedia(location_name):
    search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={location_name}&format=json"
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
def get_wikidata(location_id):
    wikidata_url = (
        f"https://www.wikidata.org/wiki/Special:EntityData/{location_id}.json"
    )
    return requests.get(wikidata_url).json().get("entities", {}).get(location_id, {})


# Function to check if an entity represents a location based on Wikidata claims
def is_location(claims):
    # Check for the 'instance of' property
    instances = claims.get("P31", [])
    for instance in instances:
        instance_id = instance["mainsnak"]["datavalue"]["value"]["id"]
        if instance_id in location_types:  # Common location types in Wikidata
            return True
    return False


# Centralized function to retrieve both label and description
def get_entity_info(entity_id):
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "ids": entity_id,
        "format": "json",
        "props": "labels|descriptions",
        "languages": "en",  # Request the label and description in English
    }
    response = requests.get(url, params=params)
    data = response.json()
    entity = data["entities"][entity_id]

    # Get label and description
    label = entity["labels"]["en"]["value"] if "en" in entity["labels"] else np.nan
    description = (
        entity["descriptions"]["en"]["value"]
        if "en" in entity["descriptions"]
        else np.nan
    )

    return label, description


# Function to get continent from Wikidata claims
def get_continent(claims):
    # P30 is the property for "continent"
    continents = claims.get("P30", [])
    if not continents:
        return np.nan, np.nan

    continent_labels = []
    continent_ids = []

    for continent in continents:
        continent_id = (
            continent.get("mainsnak", {})
            .get("datavalue", {})
            .get("value", {})
            .get("id", np.nan)
        )
        if not pd.isna(continent_id):
            continent_label, _ = get_entity_info(continent_id)  # Get only the label
            continent_labels.append(continent_label)
            continent_ids.append(continent_id)

    return (np.nan, np.nan) if not continent_ids else (continent_labels, continent_ids)


# Function to get country from Wikidata claims, considering the latest by start date
def get_country(claims):
    # P17 is the property for "country"
    country_ids = claims.get("P17", [])
    if not country_ids:
        return np.nan, np.nan

    countries = []
    for country in country_ids:
        country_id = (
            country.get("mainsnak", {})
            .get("datavalue", {})
            .get("value", {})
            .get("id", np.nan)
        )
        start_time = (
            country.get("qualifiers", {})
            .get("P580", [{}])[0]
            .get("datavalue", {})
            .get("value", {})
            .get("time", None)
        )

        if not pd.isna(country_id):
            countries.append((country_id, start_time))

    # Sort by start date, and take the latest country
    sorted_countries = sorted(
        countries, key=lambda x: x[1] if x[1] else "", reverse=True
    )
    latest_country_id = sorted_countries[0][0]
    latest_country_label, _ = get_entity_info(latest_country_id)  # Get only the label
    return latest_country_label, latest_country_id


# Function to get an image URL from Wikidata claims
def get_image_url(claims):
    # P18 is the property for "image"
    image_data = claims.get("P18", [{}])[0]
    if "mainsnak" in image_data:
        image_filename = (
            image_data.get("mainsnak", {}).get("datavalue", {}).get("value", np.nan)
        )
        if not pd.isna(image_filename):
            # Replace spaces with underscores and URL-encode special characters
            image_filename = image_filename.replace(" ", "_")
            from urllib.parse import quote

            image_filename = quote(image_filename)
            # Construct the URL for the image
            image_url = (
                f"https://commons.wikimedia.org/wiki/Special:FilePath/{image_filename}"
            )
            return image_url

    return np.nan


# Function to get coordinates from Wikidata claims
def get_coordinates(claims):
    # P625 is the property for "coordinates"
    coord_data = claims.get("P625", [{}])[0]
    if "mainsnak" in coord_data:
        coordinates = (
            coord_data.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        )
        latitude = coordinates.get("latitude", np.nan)
        longitude = coordinates.get("longitude", np.nan)
        return {"latitude": latitude, "longitude": longitude}

    return {"latitude": np.nan, "longitude": np.nan}


# Function to get the Wikipedia description of a location
def get_wikipedia_description(page_title):
    """
    Get the description or extract of a Wikipedia page.

    Args:
        page_title (str): The title of the Wikipedia page.

    Returns:
        str: The extract or description of the Wikipedia page.
    """
    wikipedia_api_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&titles={page_title}&exintro=true&explaintext=true&exsentences=5&format=json"
    response = requests.get(wikipedia_api_url).json()
    pages = response.get("query", {}).get("pages", {})
    page_data = next(
        iter(pages.values())
    )  # Get the first page in the "pages" dictionary
    return page_data.get("extract", "")


# Main function to fetch location data
def fetch_wiki_info(location_name):
    search_results = search_wikipedia(location_name)

    for result in search_results[:3]:
        page_id = result["pageid"]
        title = result["title"]

        location_id = get_page_properties(page_id)

        if location_id:
            wikidata_entity = get_wikidata(location_id)
            claims = wikidata_entity.get("claims", {})

            if not is_location(claims):
                continue

            continent_label, continent_id = get_continent(claims)
            country_label, country_id = get_country(claims)
            coordinates = get_coordinates(claims)
            thumbnail_image_url = get_image_url(claims)

            # Get label and description
            label, description = get_entity_info(location_id)

            # Get Wikipedia description
            wikipedia_description = get_wikipedia_description(title)

            res = {
                "name": title,
                "label": label,
                "description": description,
                "continent": continent_label,
                "continent_id": continent_id,
                "country": country_label,
                "country_id": country_id,
                "coordinates": coordinates,
                "thumbnail_image_url": thumbnail_image_url,
                "wikipedia_description": wikipedia_description,
                "location_id": location_id,  # Record the entity ID of the location
            }

            return res

    return {"name": location_name}


# Function to fetch data in parallel using multithreading
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


# Example usage with multiple location names
location_names = ["London", "Paris", "New York", "Lancaster", "Byzantine Empire"]
location_info_df = parallel_fetch_wiki_info(location_names)
location_info_df.to_csv("data/locations.csv", index=False)
