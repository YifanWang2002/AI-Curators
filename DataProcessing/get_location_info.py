import requests
from pprint import pprint
from location_types import location_types


# Function to search Wikipedia for an artist
def search_wikipedia(location_name):
    search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={location_name}&format=json"
    print(f"Searching Wikipedia for: {location_name}")
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


# Function to check if an entity represents a location based on Wikidata claims
def is_location(claims):

    # Check for the 'instance of' property
    instances = claims.get("P31", [])
    for instance in instances:
        instance_id = instance["mainsnak"]["datavalue"]["value"]["id"]
        if instance_id in location_types: # Common location types in Wikidata
            return True
    return False

# Funtion to decode Wikidata entity identifier
def get_label(entity_id):
    url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbgetentities',
        'ids': entity_id,
        'format': 'json',
        'props': 'labels',
        'languages': 'en'  # Request the label in English
    }
    response = requests.get(url, params=params)
    data = response.json()
    entity = data['entities'][entity_id]
    label = entity['labels']['en']['value'] if 'en' in entity['labels'] else 'No label found'
    return label

# Function to get continent from Wikidata claims
def get_continents(claims):
    # P30 is the property for "continent"
    continent_ids = claims.get("P30", [])
    continents = []

    for continent in continent_ids:
        continent_id = continent.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id", "Unknown")
        if continent_id != "Unknown":
            # Decode the continent entity identifier to its label
            continent_label = get_label(continent_id)
            continents.append(continent_label)

    return continents if continents else ["Unknown"]

# Function to get country from Wikidata claims
def get_country(claims):
    # P17 is the property for "country"
    country_ids = claims.get("P17", [])
    countries = []

    for country in country_ids:
        country_id = country.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id", "Unknown")
        if country_id != "Unknown":
            # Decode the country entity identifier to its label
            country_label = get_label(country_id)
            countries.append(country_label)

    return countries if countries else ["Unknown"]

# Function to get an image URL from Wikidata claims
def get_image_url(claims):
    # P18 is the property for "image"
    image_data = claims.get("P18", [{}])[0]
    if "mainsnak" in image_data:
        image_filename = image_data.get("mainsnak", {}).get("datavalue", {}).get("value", "Unknown")
        if image_filename != "Unknown":
            # Replace spaces with underscores and URL-encode special characters
            image_filename = image_filename.replace(" ", "_")
            # URL encode only the filename to ensure special characters are correctly formatted
            from urllib.parse import quote
            image_filename = quote(image_filename)
            
            # Construct the URL for the image
            image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{image_filename}"
            return image_url

    return "No image available"


# Main function to fetch location data
def fetch_wikipedia_summary(location_name):
    search_results = search_wikipedia(location_name)

    print(f"Search results: {search_results[:3]}")

    for result in search_results[:3]:
        # print()
        page_id = result["pageid"]
        title = result["title"]
        print(f"Checking page: {title} (ID: {page_id})")

        wikibase_item = get_page_properties(page_id)

        if wikibase_item:
            print(f"Found Wikibase item: {wikibase_item}")
            wikidata_entity = get_wikidata(wikibase_item)
            claims = wikidata_entity.get("claims", {})

            if not is_location(claims):
                print(f"{title} is not an location. Skipping.")
                continue

            continent = get_continents(claims)
            country = get_country(claims)
            thumbnail_image_url = get_image_url(claims)

            res = {
                "continent": continent,
                "country": country,
                "thumbnail_image_url": thumbnail_image_url,
            }

            return res

    return "No page has been found"


# Example usage
location_info = fetch_wikipedia_summary("Flanders")
pprint(location_info)
