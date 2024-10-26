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


if __name__ == "__main__":
    # calculate the time taken for the entire process
    start_time = time()
    art_search = ArtSearch(data_dir=os.path.join(module_dir, 'data'))
    # search for tag
    prompt = "I like vincent's colorful artwork"
    # parse the prompt
    entity_parser = EntityParser()
    tags, artists = entity_parser.extract_entities(prompt)
    if tags:
        tag_results = art_search.search(tags, search_type='tag', k=10)
        tag_results = pd.DataFrame(tag_results)
        tag_results.columns = ['tag_name', 'similarity']
    if artists:
        name_results = art_search.search(artists, search_type='name', k=1)
        name_results = pd.DataFrame(name_results)
        name_results.columns = ['artist_name', 'similarity']
    if not tags and not artists:
        print("No tags or artists found in the prompt")

    # Filter artwork details based on artist and tag search results
    artwork_details = pd.read_csv(os.path.join(module_dir, 'data', 'dimension_tables', 'dim_artwork.csv'))
    artwork_details = artwork_details.rename(columns={'Unnamed: 0': 'index'})
    new_artwork = None
    if artists:
        new_artwork = get_artwork_by_artist(artwork_details, name_results) # 41 rows x 38 
    if artists and tags:
        new_artwork = get_artwork_by_tags(tag_results, new_artwork, module_dir) # [30 rows x 41 columns]
    # if tags:
    #     new_artwork = get_artwork_by_tags(tag_results, artwork_details, module_dir)  # [2073 rows x 40 columns]
    if not artists and not tags: # edge case
        # get 50 random artworks
        new_artwork = artwork_details.sample(n=50)

    new_artwork = new_artwork.iloc[:50]

    curator = ExhibitionCurator(metadata=artwork_details)
    use_author = True if artists else False
    exhibitions = curator.curate(new_artwork, prompt, use_author)

    print(f'Total time taken: {time() - start_time} seconds')
    
    # re-create output directory 
    output_dir = os.path.join(module_dir, 'output', prompt)
    # remove existing directory
    if os.path.exists(output_dir):
        import shutil
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    # Now save the exhibitions
    for i, exhibition in enumerate(exhibitions):
        with open(os.path.join(output_dir, f'Exhibition_{i}.json'), 'w') as f:
            json.dump(exhibition, f, indent=4)

