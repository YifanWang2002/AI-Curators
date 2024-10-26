import os
from prompt_based_exhibition.ArtSearch import ArtSearch
from prompt_based_exhibition.prompt_parser_beta import EntityParser
from prompt_based_exhibition.exhibition_curator import ExhibitionCurator
import pandas as pd
import json
from time import time
# Get the directory where the ArtSearch module is located
module_dir = os.path.dirname(os.path.abspath(__file__))

def get_artwork_by_artist(artwork_details: pd.DataFrame, artist_results: pd.DataFrame) -> pd.DataFrame:
    """
    Filter artwork details based on artist search results
    Args:
        artwork_details: DataFrame with all artwork details
        artist_results: DataFrame with artist search results
    Returns:
        DataFrame with filtered artwork details
    """
    artwork_details['name'] = artwork_details['artist_given_name'] + " " + artwork_details['artist_family_name']
    artwork_details['name'] = artwork_details['name'].str.lower()
    artist_results['artist_name'] = artist_results['artist_name'].str.lower()
    return artwork_details[artwork_details['name'] == artist_results['artist_name'].iloc[0]]

def get_artwork_by_tags(search_results: pd.DataFrame, artwork_df: pd.DataFrame, module_dir: str) -> pd.DataFrame:
    """
    Filter artwork details based on tag search results
    Args:
        search_results: DataFrame with tag search results
        artwork_df: DataFrame with artwork details (pre-filtered or complete)
        module_dir: Path to module directory
    Returns:
        DataFrame with artwork details filtered by tags
    """
    # Process tag search results
    tag_id_map = pd.read_csv(os.path.join(module_dir, 'data', 'dimension_tables', 'dim_tag.csv'), 
                            usecols=['tag_id', 'tag_name'])
    results = search_results.merge(tag_id_map, on='tag_name', how='left')
    artwork_tag_map = pd.read_csv(os.path.join(module_dir, 'data', 'dimension_tables', 'mapping_tag_artwork.csv'), 
                                usecols=['tag_id', 'artwork_id'])
    results = results.merge(artwork_tag_map, on='tag_id', how='left')
    filter_df = artwork_df.merge(results, on='artwork_id', how='inner')
    
    return filter_df


def generate_exhibitions(prompt: str, module_dir: str = None) -> list[dict]:
    """
    Generate exhibitions based on a user prompt
    
    Args:
        prompt: User input prompt describing desired artwork
        module_dir: Directory containing the module data (optional)
    
    Returns:
        List of exhibition dictionaries
    """
    # Use current directory if module_dir not provided
    if module_dir is None:
        module_dir = os.path.dirname(os.path.abspath(__file__))

    # Initialize art search
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
    
    # Filter artwork details
    artwork_details = pd.read_csv(os.path.join(module_dir, 'data', 'dimension_tables', 'dim_artwork.csv'))
    artwork_details = artwork_details.rename(columns={'Unnamed: 0': 'index'})
    
    # Get filtered artwork based on search results
    if artists and not name_results.empty:
        new_artwork = get_artwork_by_artist(artwork_details, name_results)
        if tags and not tag_results.empty:
            temp_artwork = get_artwork_by_tags(tag_results, new_artwork, module_dir)
            if temp_artwork.shape[0] >= 20:
                new_artwork = temp_artwork
    elif tags and not tag_results.empty:
        new_artwork = get_artwork_by_tags(tag_results, artwork_details, module_dir)
    else:
        new_artwork = artwork_details.sample(n=50)
    
    # Limit to 50 artworks
    new_artwork = new_artwork.iloc[:50]
    
    # Generate exhibitions
    curator = ExhibitionCurator(metadata=artwork_details)
    use_author = bool(artists)
    exhibitions = curator.curate(new_artwork, prompt, use_author)
    
    return exhibitions

if __name__ == "__main__":
    start_time = time()
    
    # Generate exhibitions
    prompt = "I like vincent's sad artwork"
    exhibitions = generate_exhibitions(prompt)
    
    print(f'Total time taken: {time() - start_time} seconds')
    
    # Save exhibitions to json files
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', prompt)
    if os.path.exists(output_dir):
        import shutil
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    for i, exhibition in enumerate(exhibitions):
        with open(os.path.join(output_dir, f'Exhibition_{i}.json'), 'w') as f:
            json.dump(exhibition, f, indent=4)
