import requests
import csv
import time
from tqdm import tqdm  


# Define the base URL for the Met Museum API
BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1/objects"

# Function to fetch object IDs
def fetch_object_ids():
    response = requests.get(BASE_URL)
    if response.status_code == 200:
        return response.json()['objectIDs']
    else:
        print("Failed to fetch object IDs")
        return []

# Function to fetch individual object details
def fetch_object_details(object_id):
    url = f"{BASE_URL}/{object_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch details for object ID {object_id}")
    except Exception as e:
        print(f"Error fetching details for object ID {object_id}: {e}")
    return None

# Function to save data to CSV
def save_to_csv(filename, data):
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        writer.writerow(data)

fieldnames = [
    'objectID', 'isHighlight', 'accessionNumber', 'accessionYear', 'isPublicDomain',
    'primaryImage', 'primaryImageSmall', 'additionalImages', 'constituents',
    'department', 'objectName', 'title', 'culture', 'period', 'dynasty', 'reign',
    'portfolio', 'artistRole', 'artistPrefix', 'artistDisplayName', 'artistDisplayBio',
    'artistSuffix', 'artistAlphaSort', 'artistNationality', 'artistBeginDate',
    'artistEndDate', 'artistGender', 'artistWikidata_URL', 'artistULAN_URL',
    'objectDate', 'objectBeginDate', 'objectEndDate', 'medium', 'dimensions',
    'measurements', 'creditLine', 'geographyType', 'city', 'state', 'county', 'country',
    'region', 'subregion', 'locale', 'locus', 'excavation', 'river', 'classification',
    'rightsAndReproduction', 'linkResource', 'metadataDate', 'repository', 'objectURL',
    'tags', 'objectWikidata_URL', 'isTimelineWork', 'GalleryNumber'
]


# Function to find the last saved object ID
def get_last_saved_object_id(filename):
    try:
        with open(filename, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            if rows:
                return int(rows[-1]['objectID'])
            else:
                return None
    except FileNotFoundError:
        return None

def main():
    object_ids = fetch_object_ids()
    filename = "MET_collections.csv"

    # Write headers if the file doesn't exist
    if get_last_saved_object_id(filename) is None:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

    # Get the last saved object ID
    last_saved_id = get_last_saved_object_id(filename)

    # Start processing from the next object ID
    start_index = object_ids.index(last_saved_id) + 1 if last_saved_id else 0

    # Process each object ID with a progress bar
    for object_id in tqdm(object_ids[start_index:]):
        details = fetch_object_details(object_id)
        if details:
            save_to_csv(filename, details)
        time.sleep(0.05)  # Sleep to avoid rate limiting

if __name__ == "__main__":
    main()
