import json
import requests
import pandas as pd
import time
import tqdm
import os

FIELDS_TO_KEEP = ["id", "accession_number", "share_license_status", "tombstone", "current_location", "title", "title_in_original_language",
                  "series", "series_in_original_language", "creation_date", "creation_date", "creation_date_earliest", "creation_date_latest",
                  "creators", "culture", "technique", "support_materials", "department", "collection", "type", "measurements", "dimensions",
                  "state_of_the_work", "edition_of_the_work", "creditline", "copyright", "inscriptions", "exhibitions", "provenance", "find_spot",
                  "related_works", "did_you_know", "description", "citations", "catalogue_raisonne", "url", "images", "alternate_images", "sketchfab_id",
                  "sketchfab_url", "updated_at", "legal_status", "accession_date", "sortable_date", "date_text", "collapse_artists", "on_loan", "recently_acquired",
                  "record_type", "conservation_statement", "is_nazi_era_provenance", "impression", "alternate_titles", "is_highlight", "current_exhibition"]

CSV_FILE = 'data/tcma_raw.csv'
API_URL = "https://openaccess-api.clevelandart.org/api/artworks/"

# Ensure the 'data' folder exists
if not os.path.exists('data'):
    os.makedirs('data')

def fetch_artwork_data(skip=0, limit=1):
    try:
        request_url = f"{API_URL}?limit={limit}&skip={skip}&has_image=1&cc0=1&type=Painting"
        response = requests.get(request_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        return data['data']
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return "ERROR"
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return "ERROR"
    except KeyError as e:
        print(f"Key error: {e}")
        return "ERROR"

def save_to_csv(data, fields, csv_file):
    df = pd.DataFrame(data, columns=fields)
    df.to_csv(csv_file, mode='a', header=False, index=False)

if __name__ == "__main__":
    # Initialize the CSV file with headers
    df = pd.DataFrame(columns=FIELDS_TO_KEEP)
    df.to_csv(CSV_FILE, index=False)

    batch_size = 100  # Fetch multiple records per request for efficiency

    # Total records fetched counter
    total_records_fetched = 0
    skip = 0
    progressionBar = tqdm.tqdm(desc="Downloading Artworks", unit="record")

    while True:
        data = fetch_artwork_data(skip, batch_size)
        
        if data == "ERROR":
            print(f"Failed to fetch records starting at {skip}. Retrying...")
            time.sleep(5)  # Wait before retrying
            continue
        
        if not data:
            break  # Exit the loop if no data is returned

        processed_data = []
        for painting in data:
            data_dict = {field: painting.get(field, None) for field in FIELDS_TO_KEEP}
            processed_data.append(data_dict)

        save_to_csv(processed_data, FIELDS_TO_KEEP, CSV_FILE)
        records_fetched = len(processed_data)
        total_records_fetched += records_fetched

        print(f"Appended {records_fetched} records to CSV. Total records fetched={total_records_fetched}")
        skip += batch_size
        progressionBar.update(records_fetched)

        # Sleep to avoid hitting the API rate limits
        time.sleep(1)

    progressionBar.close()
    print(f"Finished downloading {total_records_fetched} records.")