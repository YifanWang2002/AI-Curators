import requests
import sys

DATABASE_URL = "http://localhost:8000/api/"
    
def get_artwork_by_id(artwork_id):
    url = f"{DATABASE_URL}/data/artwork/{artwork_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}
    
def get_artworks_by_tag(tag_id):
    url = f"{DATABASE_URL}/data/mapping_tag_artwork/{tag_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}

def get_tags_by_artwork(artwork_id):
    url = f"{DATABASE_URL}/data/mapping_artwork_tag/{artwork_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}

def get_tag_by_id(tag_id):
    url = f"{DATABASE_URL}/data/tag/{tag_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}

def get_tag_by_type(tag_type):
    url = f"{DATABASE_URL}/data/tag_type/{tag_type}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}

def get_tag_count_by_type(tag_type):
    url = f"{DATABASE_URL}/data/tag_type/count/{tag_type}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}

def get_all_tags():
    url = f"{DATABASE_URL}/data/tags"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}

def get_tag_score_by_id(tag_id):
    url = f"{DATABASE_URL}/data/tag_score/{tag_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}

def get_artwork_score_by_id(artwork_id):
    url = f"{DATABASE_URL}/data/artwork_score/{artwork_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}
    
def get_artist_by_id(artist_id):
    url = f"{DATABASE_URL}/data/artist/{artist_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}

def get_artist_by_name(artist_name, fuzzy=False):
    if fuzzy:
        url = f"{DATABASE_URL}/data/artist/name_fuzzy/{artist_name}"
    else:
        url = f"{DATABASE_URL}/data/artist/name/{artist_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}

def get_location_by_name(location):
    url = f"{DATABASE_URL}/data/location/{location}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}
    

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_artist.py [artist_id]")
        sys.exit(1)
    
    artist_id = sys.argv[1]
    result = get_artist_by_id(artist_id)
    print(result)