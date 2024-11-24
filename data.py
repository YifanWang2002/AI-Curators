import os

import pandas as pd
import requests

DATABASE_URL = os.getenv('DATABASE_URL', 'http://localhost:8000/api/data')


def get_data(url):
    """Generic function to fetch data from API endpoint"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {'status': 'error', 'message': str(e)}

def get_all_artworks():
    """Fetch all artworks from MongoDB"""
    try:
        # First get all artwork IDs
        ids_response = get_data(f"{DATABASE_URL}/artworks/ids")
        if ids_response.get('status') != 'success':
            return {'status': 'error', 'message': 'Failed to fetch artwork IDs'}
        
        artwork_ids = ids_response['data']
        
        # Then fetch artworks in batches
        all_artworks = []
        batch_size = 100
        url = f"{DATABASE_URL}/artworks"
        
        for i in range(0, len(artwork_ids), batch_size):
            batch_ids = artwork_ids[i:i + batch_size]
            payload = {"artwork_ids": batch_ids}
            response = requests.post(url, json=payload)
            
            if response.status_code == 200 and response.json().get('status') == 'success':
                all_artworks.extend(response.json().get('data', []))
            else:
                print(f"Warning: Failed to fetch batch {i//batch_size + 1}")
        
        return {'status': 'success', 'data': all_artworks}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def get_tags_by_artwork_id(artwork_id):
    """Fetch tags for a specific artwork"""
    return get_data(f"{DATABASE_URL}/mapping_artwork_tag/{artwork_id}")

def get_artwork_by_tag_id(tag_id):
    """Fetch artworks for a specific tag"""
    return get_data(f"{DATABASE_URL}/mapping_tag_artwork/{tag_id}")

def get_all_tags():
    """Fetch all tags from MongoDB"""
    return get_data(f"{DATABASE_URL}/tags")

def get_artist_by_name(artist_name, fuzzy=True):
    """Fetch artist by name with option for fuzzy matching"""
    endpoint = "name_fuzzy" if fuzzy else "name"
    return get_data(f"{DATABASE_URL}/artist/{endpoint}/{artist_name}")

def convert_to_dataframe(data_list):
    """Convert API response to pandas DataFrame"""
    if not data_list:
        return pd.DataFrame()
    return pd.DataFrame(data_list)

def get_artist_by_id(artist_id):
    """Fetch artist details by artist ID"""
    return get_data(f"{DATABASE_URL}/artist/{artist_id}")

def get_artwork_details():
    """Get complete artwork details as DataFrame"""
    response = get_all_artworks()
    if response.get('status') == 'success':
        df = convert_to_dataframe(response.get('data', []))
        
        # Fetch artist details for each artwork
        artist_details = []
        for artist_id in df['artist_id'].unique():
            artist_response = get_artist_by_id(artist_id)
            if artist_response.get('status') == 'success':
                artist_details.append(artist_response['data'])
        
        # Create artist lookup DataFrame
        artist_df = pd.DataFrame(artist_details)
        
        # Merge artwork data with artist data
        if not artist_df.empty:
            df = df.merge(
                artist_df[['artist_id', 'display_name']],
                on='artist_id',
                how='left'
            )
        
        # Ensure all required columns are present
        required_columns = ['artwork_id', 'artist_id', 'display_name', 'compressed_url']
        for col in required_columns:
            if col not in df.columns:
                print(f"Warning: Missing required column {col}")
                df[col] = ''
        return df
    return pd.DataFrame()

def get_tag_mapping():
    """Get tag information as DataFrame"""
    response = get_all_tags()
    if response.get('status') == 'success':
        return convert_to_dataframe(response.get('data', []))
    return pd.DataFrame()
