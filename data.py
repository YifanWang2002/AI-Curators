import requests
import pandas as pd
import os
import time

DATABASE_URL = os.getenv('DATABASE_URL', 'http://localhost:8000/api/data')

def get_data(url, max_retries=3):
    """Generic function to fetch data from API endpoint with retries"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            if response.status_code == 200:
                return response.json()
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                print(f"Failed to connect to {url} after {max_retries} attempts: {str(e)}")
                return {'status': 'error', 'message': str(e)}
            print(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(1)

def get_all_artworks():
    """Fetch all artworks from MongoDB"""
    try:
        # First get all artwork IDs
        ids_response = get_data(f"{DATABASE_URL}/artworks/ids")
        if ids_response.get('status') != 'success':
            print(f"Failed to fetch artwork IDs: {ids_response.get('message')}")
            return {'status': 'error', 'message': 'Failed to fetch artwork IDs'}
        
        artwork_ids = ids_response['data']
        
        # Use the POST endpoint for batch fetching
        response = requests.post(
            f"{DATABASE_URL}/artworks",
            json={'artwork_ids': artwork_ids}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch artworks: {response.text}")
            return {'status': 'error', 'message': 'Failed to fetch artworks'}
        
    except Exception as e:
        print(f"Error in get_all_artworks: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def get_artwork_details():
    """Get complete artwork details as DataFrame"""
    response = get_all_artworks()
    if response.get('status') == 'success':
        artworks = response.get('data', [])
        if not artworks:
            print("Warning: No artwork data received")
            return pd.DataFrame()
            
        df = pd.DataFrame(artworks)
        
        # Map the columns based on the actual MongoDB schema
        column_mapping = {
            'artwork_id': 'artwork_id',
            'artist_given_name': 'given_name',  # from artist info
            'artist_family_name': 'family_name',  # from artist info
            'artwork_name': 'title',
            'artwork_date': 'creation_year_start',
            'artwork_type': 'type',
            'artwork_material': 'medium'
        }
        
        # Create new columns with mapped names
        for new_col, old_col in column_mapping.items():
            if old_col not in df.columns:
                df[new_col] = ''
            else:
                df[new_col] = df[old_col]
        
        return df
    else:
        print(f"Error getting artwork details: {response.get('message')}")
        return pd.DataFrame()

def get_tags_by_artwork_id(artwork_id):
    """Fetch tags for a specific artwork"""
    try:
        response = get_data(f"{DATABASE_URL}/mapping_artwork_tag/{artwork_id}")
        if response and response.get('status') == 'success':
            # Deduplicate tags while maintaining order
            seen = set()
            unique_tags = [x for x in response['data'] if not (x in seen or seen.add(x))]
            return {'status': 'success', 'data': unique_tags}
        print(f"Error fetching tags for artwork {artwork_id}: {response.get('message')}")
        return response
    except Exception as e:
        print(f"Error in get_tags_by_artwork_id: {str(e)}")
        return {'status': 'error', 'message': str(e)}
    
def get_artwork_by_tag_id(tag_id):
    """Fetch artworks for a specific tag"""
    try:
        response = get_data(f"{DATABASE_URL}/mapping_tag_artwork/{tag_id}")
        if response and response.get('status') == 'success':
            # Deduplicate artworks while maintaining order
            seen = set()
            unique_artworks = [x for x in response['data'] if not (x in seen or seen.add(x))]
            return {'status': 'success', 'data': unique_artworks}
        return response
    except Exception as e:
        print(f"Error in get_artwork_by_tag_id: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def get_tag_mapping():
    """Get tag information as DataFrame"""
    response = get_all_tags()
    if response.get('status') == 'success':
        tags = response.get('data', [])
        if not tags:
            print("Warning: No tags received from database")
            return pd.DataFrame()
            
        # columns: '_id', 'action_count', 'count', 'description', 'tag_id', 
        # 'tag_name', 'tag_type', 'thumbnail_image_url'
        df = pd.DataFrame(tags) 
        
        # Map the columns based on the actual MongoDB schema
        required_columns = {
            'tag_id': 'tag_id',
            'tag_name': 'tag_name',  
            'tag_type': 'tag_type'
        }
        
        # Create new DataFrame with required columns
        result_df = pd.DataFrame()
        for new_col, old_col in required_columns.items():
            if old_col in df.columns:
                result_df[new_col] = df[old_col]
            else:
                print(f"Warning: Missing column '{old_col}' in tag data")
                result_df[new_col] = ''
        
        if not result_df.empty:
            print(f"Successfully mapped {len(result_df)} tags with columns: {result_df.columns.tolist()}")
            return result_df
        else:
            print("Warning: Tag mapping resulted in empty DataFrame")
            return pd.DataFrame()
    else:
        print(f"Error getting tags: {response.get('message')}")
        return pd.DataFrame()
    
def get_artwork_by_tags(search_results: pd.DataFrame, artwork_df: pd.DataFrame) -> pd.DataFrame:
    """Filter artwork details based on tag search results using MongoDB data"""
    tag_mapping = get_tag_mapping()
    if tag_mapping.empty:
        print("Warning: No tag mapping data available")
        return artwork_df
    
    # Merge search results with tag mapping
    results = search_results.merge(tag_mapping[['tag_id', 'tag_name']], on='tag_name', how='left')
    
    # Get unique tag IDs
    unique_tag_ids = results['tag_id'].dropna().unique()
    print(f"Found {len(unique_tag_ids)} unique matching tags")
    
    # Get artwork IDs for matching tags
    artwork_ids = set()
    for tag_id in unique_tag_ids:
        response = get_artwork_by_tag_id(int(tag_id))
        if response and response.get('status') == 'success':
            new_artworks = set(response['data'])  # Convert to set for deduplication
            artwork_ids.update(new_artworks)
            print(f"Found {len(new_artworks)} unique artworks for tag {tag_id}")
    
    if not artwork_ids:
        print("Warning: No artwork IDs found for the given tags")
        return artwork_df
    
    filtered_df = artwork_df[artwork_df['artwork_id'].isin(artwork_ids)]
    print(f"Filtered to {len(filtered_df)} unique artworks based on tags")
    
    return filtered_df

def get_all_tags():
    """Fetch all tags from MongoDB"""
    response = get_data(f"{DATABASE_URL}/tags")
    if response.get('status') != 'success':
        print(f"Error fetching tags: {response.get('message')}")
    return response



if __name__ == "__main__":
    # Test connection and data retrieval
    print("Testing API connection...")
    response = get_data(f"{DATABASE_URL}/artworks/ids")
    print(f"Connection test response: {response.get('status')}")
    
    print("\nTesting artwork retrieval...")
    artworks = get_artwork_details()
    print(f"Retrieved {len(artworks)} artworks")
    if not artworks.empty:
        print("Sample columns:", artworks.columns.tolist())
    
    print("\nTesting tag retrieval...")
    tags = get_all_tags()
    if tags.get('status') == 'success':
        tag_data = tags.get('data', [])
        print(f"Retrieved {len(tag_data)} tags")
        if tag_data:
            print("Sample tag data:", tag_data[0])
            
    print("\nTesting tag mapping...")
    tag_mapping = get_tag_mapping()
    if not tag_mapping.empty:
        print(f"Mapped {len(tag_mapping)} tags")
        print("Tag mapping columns:", tag_mapping.columns.tolist())

    