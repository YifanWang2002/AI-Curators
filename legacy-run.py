import os
from prompt_based_exhibition.ArtSearch import ArtSearch
from prompt_based_exhibition.prompt_parser_beta import EntityParser
from prompt_based_exhibition.exhibition_curator import ExhibitionCurator
import pandas as pd
import json
from time import time

import data

def get_artwork_by_artist(artwork_details: pd.DataFrame, artist_results: pd.DataFrame) -> pd.DataFrame:
    """
    Filter artwork details based on artist search results
    """
    artwork_details['name'] = artwork_details['artist_given_name'].fillna('') + " " + artwork_details['artist_family_name'].fillna('')
    artwork_details['name'] = artwork_details['name'].str.lower()
    artist_results['artist_name'] = artist_results['artist_name'].str.lower()
    return artwork_details[artwork_details['name'] == artist_results['artist_name'].iloc[0]]

def get_artwork_by_tags(search_results: pd.DataFrame, artwork_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter artwork details based on tag search results using MongoDB data
    """
    # Process tag search results
    tag_mapping = data.get_tag_mapping()
    if tag_mapping.empty:
        print("Warning: No tag mapping data available")
        return artwork_df
    
    results = search_results.merge(tag_mapping[['tag_id', 'tag_name']], on='tag_name', how='left')
    
    # Get artwork IDs for matching tags
    artwork_ids = set()
    for tag_id in results['tag_id'].dropna():
        response = data.get_artwork_by_tag_id(int(tag_id))
        if response.get('status') == 'success':
            artwork_ids.update(response['data'])
    
    if not artwork_ids:
        print("Warning: No artwork IDs found for the given tags")
        return artwork_df
    
    return artwork_df[artwork_df['artwork_id'].isin(artwork_ids)]

def prepare_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare metadata DataFrame with proper index and columns
    """
    # Reset index and ensure it starts from 0
    df = df.reset_index(drop=True)
    
    # Add the index column that ExhibitionCurator expects
    df['index'] = df.index
    
    # Ensure all required columns exist
    required_columns = [
        'index', 'artwork_id', 'artist_given_name', 'artist_family_name',
        'artwork_name', 'artwork_date', 'artwork_type', 'artwork_material'
    ]
    
    for col in required_columns:
        if col not in df.columns:
            df[col] = ''
            
    return df

def generate_exhibitions(prompt: str, module_dir: str = None) -> list[dict]:
    """
    Generate exhibitions based on a user prompt using MongoDB data
    """
    if module_dir is None:
        module_dir = os.path.dirname(os.path.abspath(__file__))

    # Initialize art search with index files only
    art_search = ArtSearch(data_dir=os.path.join(module_dir, 'data'))
    
    # Parse the prompt
    entity_parser = EntityParser()
    tags, artists = entity_parser.extract_entities(prompt)
    
    # Search for tags and artists
    tag_results = pd.DataFrame()
    name_results = pd.DataFrame()
    if tags:
        tag_results = pd.DataFrame(art_search.search(tags, search_type='tag', k=20),
                                 columns=['tag_name', 'similarity'])
    if artists:
        name_results = pd.DataFrame(art_search.search(artists, search_type='name', k=1),
                                  columns=['artist_name', 'similarity'])
    
    # Get artwork details from MongoDB
    artwork_details = data.get_artwork_details()
    if artwork_details.empty:
        print("Error: Unable to retrieve artwork details from database")
        return []
    
    # Prepare metadata with proper index
    artwork_details = prepare_metadata(artwork_details)
    
    print(f"Retrieved {len(artwork_details)} artworks from database")
    
    # Get filtered artwork based on search results
    if artists and not name_results.empty:
        
        artist_given_names = []
        artist_family_names = []
        for artist_id in artwork_details['artist_id']:
            # check if artist_id is NaN
            if pd.isnull(artist_id):
                artist_given_names.append('')
                artist_family_names.append('')
                continue
            artist_data = data.get_artist_by_id(int(artist_id))['data']
            family_name = artist_data['family_name']
            given_name = artist_data['given_name']
            artist_given_names.append(given_name)
            artist_family_names.append(family_name)
        artwork_details['artist_given_name'] = artist_given_names
        artwork_details['artist_family_name'] = artist_family_names

        new_artwork = get_artwork_by_artist(artwork_details, name_results)
        if tags and not tag_results.empty:
            temp_artwork = get_artwork_by_tags(tag_results, new_artwork)
            if temp_artwork.shape[0] >= 20:
                new_artwork = temp_artwork
    elif tags and not tag_results.empty:
        new_artwork = get_artwork_by_tags(tag_results, artwork_details)
    else:
        new_artwork = artwork_details.sample(n=min(50, len(artwork_details)))
    
    # Prepare the filtered artwork data
    new_artwork = prepare_metadata(new_artwork)
    print(f"Filtered to {len(new_artwork)} relevant artworks")
    
    # Limit to 50 artworks
    new_artwork = new_artwork.iloc[:50]
    
    # Generate exhibitions
    curator = ExhibitionCurator(metadata=artwork_details)
    use_author = bool(artists)
    exhibitions = curator.curate(new_artwork, prompt, use_author)
    
    return exhibitions

if __name__ == "__main__":
    start_time = time()
    prev_time = time()
    
    # Generate exhibitions
    # prompts = ["I want to see Vincent van Gogh's use of color and brushstrokes"]
    prompts = ['I want to see loneliness and depression', 
               'I want to see happiness and joy',
               'I want to see nature and animals',
               'Artworks of water and mountain',
               'I want to see flowers',]
    for prompt in prompts:
        exhibitions = generate_exhibitions(prompt)
        
        print(f'Time taken: {time() - prev_time} seconds')
        prev_time = time()
        
        # Save exhibitions to json files
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output_new2', prompt)

        if os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)
        os.makedirs(output_dir)
        
        for i, exhibition in enumerate(exhibitions):
            with open(os.path.join(output_dir, f'Exhibition_{i}.json'), 'w') as f:
                json.dump(exhibition, f, indent=4)
    print(f'Total time taken: {time() - start_time} seconds')