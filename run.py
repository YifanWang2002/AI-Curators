import os
from prompt_based_exhibition.ArtSearch import ArtSearch
from prompt_based_exhibition.prompt_parser_beta import EntityParser
from prompt_based_exhibition.exhibition_curator import ExhibitionCurator
import pandas as pd
import json
from time import time
import data

# artists_dict = data.get_all_artists()

def get_artwork_by_artist(artwork_details: pd.DataFrame, artist_results: pd.DataFrame) -> pd.DataFrame:
    """
    Filter artwork details based on artist search results and store name similarity
    """
    artwork_details['name'] = artwork_details['artist_given_name'].fillna('') + " " + artwork_details['artist_family_name'].fillna('')
    artwork_details['name'] = artwork_details['name'].str.lower()
    artist_results['artist_name'] = artist_results['artist_name'].str.lower()
    
    filtered_artwork = artwork_details[artwork_details['name'] == artist_results['artist_name'].iloc[0]].copy()
    filtered_artwork['name_similarity'] = artist_results['similarity'].iloc[0]
    filtered_artwork = filtered_artwork.reset_index(drop=True)
    filtered_artwork['index'] = filtered_artwork.index
    
    return filtered_artwork

def get_artwork_by_tags(search_results: pd.DataFrame, artwork_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter artwork details based on tag search results with weighted similarities based on ranking
    Tags that rank higher (more relevant) contribute more to the total similarity score
    """
    tag_mapping = data.get_tag_mapping()
    if tag_mapping.empty:
        print("Warning: No tag mapping data available")
        artwork_df = artwork_df.copy()
        artwork_df['tag_similarity'] = 0
        artwork_df = artwork_df.reset_index(drop=True)
        artwork_df['index'] = artwork_df.index
        return artwork_df

    # Sort search results by similarity to ensure proper ranking
    search_results = search_results.sort_values('similarity', ascending=False).reset_index(drop=True)
    
    # Calculate rank weights using exponential decay
    # Higher ranked tags (lower index) get higher weights
    num_tags = len(search_results)
    decay_rate = 0.5  # Adjust this to control how quickly weights decay
    rank_weights = [decay_rate ** i for i in range(num_tags)]
    
    # Create dict of tag_name to (similarity, weight) pairs
    tag_info = {
        row['tag_name']: (row['similarity'], rank_weights[i])
        for i, row in search_results.iterrows()
    }
    
    # Get artwork IDs and their associated weighted tag similarities
    artwork_total_similarity = {}
    for tag_name, (similarity, weight) in tag_info.items():
        try:
            tag_id = tag_mapping[tag_mapping['tag_name'] == tag_name]['tag_id'].iloc[0]
            response = data.get_artwork_by_tag_id(int(tag_id))
            if response.get('status') == 'success':
                # Add weighted similarity score to each artwork's total
                weighted_similarity = similarity * weight
                for artwork_id in response['data']:
                    artwork_total_similarity[artwork_id] = artwork_total_similarity.get(artwork_id, 0) + weighted_similarity
        except IndexError:
            print(f"Warning: Tag '{tag_name}' not found in mapping")
            continue
    
    if not artwork_total_similarity:
        print("Warning: No artwork IDs found for the given tags")
        artwork_df = artwork_df.copy()
        artwork_df['tag_similarity'] = 0
        artwork_df = artwork_df.reset_index(drop=True)
        artwork_df['index'] = artwork_df.index
        return artwork_df
    
    # Normalize the similarity scores to [0, 1] range
    max_similarity = max(artwork_total_similarity.values())
    if max_similarity > 0:
        artwork_total_similarity = {
            k: v / max_similarity 
            for k, v in artwork_total_similarity.items()
        }
    
    # Filter artwork and add weighted similarity scores
    filtered_artwork = artwork_df[artwork_df['artwork_id'].isin(artwork_total_similarity.keys())].copy()
    filtered_artwork['tag_similarity'] = filtered_artwork['artwork_id'].map(artwork_total_similarity)
    filtered_artwork = filtered_artwork.reset_index(drop=True)
    filtered_artwork['index'] = filtered_artwork.index
    
    return filtered_artwork

def generate_exhibitions(prompt: str, art_search, module_dir: str = None) -> list[dict]:
    """
    Generate exhibitions based on a user prompt using MongoDB data
    """
    
    artwork_details = data.get_artwork_details()
    if artwork_details.empty:
        print("Error: Unable to retrieve artwork details from database")
        return []
    
    print(f"Retrieved {len(artwork_details)} artworks from database")
    
    # Get filtered artwork based on search results
    # artwork_details['artist_id'] = artwork_details['artist_id'].fillna(-1)
    # artwork_details['artist_id'] = artwork_details['artist_id'].astype(int)
    # for i in range(len(artwork_details)):
    #     artist_id = artwork_details.loc[i, 'artist_id']
    #     if artist_id == -1 or artist_id not in artists_dict:
    #         artwork_details.loc[i, 'display_name'] = 'unknown artist'
    #         artwork_details.loc[i, 'artist_given_name'] = ''
    #         artwork_details.loc[i, 'artist_family_name'] = ''
    #         continue
    #     artist_given_name = artists_dict[artist_id]['given_name']
    #     artist_family_name = artists_dict[artist_id]['family_name']
    #     if artist_family_name is None and artist_given_name is None:
    #         artwork_details.loc[i, 'display_name'] = 'unknown artist'
    #         artwork_details.loc[i, 'artist_given_name'] = ''
    #         artwork_details.loc[i, 'artist_family_name'] = ''
    #         continue
    #     elif artist_family_name is None:
    #         artist_family_name = ''
    #     elif artist_given_name is None:
    #         artist_given_name = ''
    #     artist_name = artist_given_name + " " + artist_family_name
    #     artwork_details.loc[i, 'display_name'] = artist_name
    #     artwork_details.loc[i, 'artist_given_name'] = artist_given_name
    #     artwork_details.loc[i, 'artist_family_name'] = artist_family_name

    # if module_dir is None:
    #     module_dir = os.path.dirname(os.path.abspath(__file__))
    # art_search = ArtSearch(data_dir=os.path.join(module_dir, 'data'), use_precomputed=True)

    entity_parser = EntityParser()
    tags, artists = entity_parser.extract_entities(prompt)
    
    tag_results = pd.DataFrame()
    name_results = pd.DataFrame()
    if tags:
        tag_results = pd.DataFrame(art_search.search(tags, search_type='tag', k=25),
                                 columns=['tag_name', 'similarity'])
        # print(f"Tags: {tag_results}")
        # print(f"Similarity results for tags: {tag_results[:5]}")
    if artists:
        name_results = pd.DataFrame(art_search.search(artists, search_type='name', k=1),
                                  columns=['artist_name', 'similarity'])
        # print(f"Artists: {name_results}")
    
    # Add index column to artwork_details
    artwork_details = artwork_details.reset_index(drop=True)
    artwork_details['index'] = artwork_details.index
    
    if artists and not name_results.empty:
        new_artwork = get_artwork_by_artist(artwork_details, name_results)
        if tags and not tag_results.empty:
            temp_artwork = get_artwork_by_tags(tag_results, new_artwork)
            if temp_artwork.shape[0] >= 20:
                new_artwork = temp_artwork
    elif tags and not tag_results.empty:
        new_artwork = get_artwork_by_tags(tag_results, artwork_details)
    else:
        new_artwork = artwork_details.sample(n=min(50, len(artwork_details)))
        new_artwork['tag_similarity'] = 0
        new_artwork['name_similarity'] = 0
        new_artwork = new_artwork.reset_index(drop=True)
        new_artwork['index'] = new_artwork.index
    
    print(f"Filtered to {len(new_artwork)} relevant artworks")
    
    # Sort by total tag similarity and reset index
    if 'tag_similarity' in new_artwork.columns:
        new_artwork = new_artwork.sort_values('tag_similarity', ascending=False)
        new_artwork = new_artwork.reset_index(drop=True)
        new_artwork['index'] = new_artwork.index
    
    # Limit to 50 artworks
    new_artwork = new_artwork.iloc[:50]
    # Reset index one final time to ensure it's sequential for the top 50
    new_artwork = new_artwork.reset_index(drop=True)
    new_artwork['index'] = new_artwork.index
    
    # Generate exhibitions
    curator = ExhibitionCurator(metadata=artwork_details)
    use_author = bool(artists)
    exhibitions = curator.curate(new_artwork, prompt, use_author)
    
    return exhibitions

if __name__ == "__main__":
    start_time = time()

    # prompt = "I like old age artworks"
    # prompt = "I like countryside artwork"
    prompts = ["I want to see happiness and joy",]
    module_dir = os.path.dirname(os.path.abspath(__file__))
    art_search = ArtSearch(data_dir=os.path.join(module_dir, 'data'), use_precomputed=True)
    # prompts = ["I want to see van Gogh's use of color and brushstrokes",
    #            "I want to see artworks by Monet",
    #            'I want to see loneliness and depression', 
    #            'I want to see happiness and joy',
    #            'I want to see nature and animals',
    #            'Artworks of water and mountain',
    #            'I want to see flowers',]
    for prompt in prompts:
        exhibitions = generate_exhibitions(prompt, art_search)
        print(f'Total time taken: {time() - start_time} seconds')
        
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', prompt)
        if os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)
        os.makedirs(output_dir)
        
        for i, exhibition in enumerate(exhibitions):
            with open(os.path.join(output_dir, f'Exhibition_{i}.json'), 'w') as f:
                json.dump(exhibition, f, indent=4)