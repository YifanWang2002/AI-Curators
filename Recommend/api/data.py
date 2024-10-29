import requests
import sys

DATABASE_URL = "http://localhost:8000/api"

def get_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}
    
def get_artwork_by_id(artwork_id):
    url = f"{DATABASE_URL}/data/artwork/{artwork_id}"
    return get_data(url)

def get_artworks_by_ids(artwork_ids):
    artworks_ids_str = ",".join(artwork_ids)
    url = f"{DATABASE_URL}/data/artworks/{artworks_ids_str}"
    return get_data(url)

def get_artworks_id_mapping():
    url = f"{DATABASE_URL}/data/artworks/id_mapping"
    return get_data(url)

def get_all_artworks_ids():
    url = f"{DATABASE_URL}/data/artworks/ids"
    return get_data(url)

def get_exhibition_by_id(exhibition_id):
    url = f"{DATABASE_URL}/data/exhibition/{exhibition_id}"
    return get_data(url)
    
def get_art_pieces_in_exhibition(exhibition_id):
    url = f"{DATABASE_URL}/data/exhibition/art_pieces/{exhibition_id}"
    return get_data(url)

def get_all_exhibitions():
    url = f"{DATABASE_URL}/data/exhibitions"
    return get_data(url)

def get_all_exhibitions_ids():
    url = f"{DATABASE_URL}/data/exhibitions/ids"
    return get_data(url)
    
def get_artworks_by_tag_id(tag_id):
    url = f"{DATABASE_URL}/data/mapping_tag_artwork/{tag_id}"
    return get_data(url)

def get_tags_by_artwork_id(artwork_id):
    url = f"{DATABASE_URL}/data/mapping_artwork_tag/{artwork_id}"
    return get_data(url)
    
def get_exhibitions_by_tag_id(tag_id):
    url = f"{DATABASE_URL}/data/mapping_tag_exhibition/{tag_id}"
    return get_data(url)

def get_tags_by_exhibition_id(exhibition_id):
    url = f"{DATABASE_URL}/data/mapping_exhibition_tag/{exhibition_id}"
    return get_data(url)

def get_tag_by_id(tag_id):
    url = f"{DATABASE_URL}/data/tag/{tag_id}"
    return get_data(url)

def get_tags_by_type(tag_type):
    url = f"{DATABASE_URL}/data/tag_type/{tag_type}"
    return get_data(url)

def get_tag_count_by_type(tag_type):
    url = f"{DATABASE_URL}/data/tag_type/count/{tag_type}"
    return get_data(url)

def get_all_tags():
    url = f"{DATABASE_URL}/data/tags"
    return get_data(url)

def get_clickstream_records_by_user(user_id):
    url = f"{DATABASE_URL}/data/clickstreams/user/{user_id}"
    return get_data(url)

def get_clicked_artworks_by_user(user_id):
    url = f"{DATABASE_URL}/data/clickstreams/click/artworks/{user_id}"
    return get_data(url)

def get_clicked_exhibitions_by_user(user_id):
    url = f"{DATABASE_URL}/data/clickstreams/click/exhibitions/{user_id}"
    return get_data(url)

def get_tag_preferences_by_user(user_id):
    url = f"{DATABASE_URL}/data/user_recommendation/{user_id}/tag_preference"
    return get_data(url)

def get_tag_score_by_id(tag_id):
    url = f"{DATABASE_URL}/data/tag_score/{tag_id}"
    return get_data(url)

def get_artwork_score_by_id(artwork_id):
    url = f"{DATABASE_URL}/data/artwork_score/{artwork_id}"
    return get_data(url)
    
def get_artist_by_id(artist_id):
    url = f"{DATABASE_URL}/data/artist/{artist_id}"
    return get_data(url)

def get_artist_by_name(artist_name, fuzzy=False):
    if fuzzy:
        url = f"{DATABASE_URL}/data/artist/name_fuzzy/{artist_name}"
    else:
        url = f"{DATABASE_URL}/data/artist/name/{artist_name}"
    return get_data(url)

def get_location_by_name(location):
    url = f"{DATABASE_URL}/data/location/{location}"
    return get_data(url)
    

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python data.py [input1] [input2](optional)")
        sys.exit(1)
    
    input1 = sys.argv[1]
    input2 = sys.argv[2] if len(sys.argv) > 2 else False
    # result = get_artist_by_name(input1, fuzzy=input2)
    result = get_clicked_artworks_by_user(input1)
    print(result)