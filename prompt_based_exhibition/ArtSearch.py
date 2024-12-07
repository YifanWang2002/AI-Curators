import os
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
import torch
import data

class ArtSearch:
    def __init__(self, data_dir="../data", use_precomputed=True):
        self.data_dir = data_dir
        self.artwork_details = data.get_artwork_details()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Load E5 model
        self.model = SentenceTransformer("intfloat/e5-large-v2")

        if use_precomputed:
            self.load_precomputed_data()
        else:
            self.load_data()
            self.create_indexes()
            self.save_precomputed_data()

    def load_data(self):
        # df_names = pd.read_csv(os.path.join(self.data_dir, 'dimension_tables', 'dim_artwork.csv'))
        df_names = self.artwork_details
        # self.artist_names = (df_names['artist_given_name'] + ' ' + df_names['artist_family_name']).dropna().unique()
        self.artist_names = df_names['display_name'].dropna().unique()
        # remove names with all spaces
        # self.artist_names = [name for name in self.artist_names if name.strip() != '']

        df_tags = pd.read_csv(os.path.join(self.data_dir, 'dimension_tables', 'dim_tag.csv'))
        self.tags = df_tags['tag_name'].dropna().unique()

    def create_indexes(self):
        self.name_index = self.create_index(self.artist_names)
        self.tag_index = self.create_index(self.tags)

    def create_index(self, items):
        embeddings = self.model.encode(items, normalize_embeddings=True)
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        return index
    
    def load_precomputed_data(self):
        index_dir = os.path.join(self.data_dir, 'index_files')
    
        # Load FAISS indexes
        self.name_index = faiss.read_index(os.path.join(index_dir, 'name_index.index'))
        self.tag_index = faiss.read_index(os.path.join(index_dir, 'tag_index.index'))

    def save_precomputed_data(self):
        # Create index_files directory if it doesn't exist
        index_dir = os.path.join(self.data_dir, 'index_files')
        os.makedirs(index_dir, exist_ok=True)
        
        # Save FAISS indexes
        faiss.write_index(self.name_index, os.path.join(index_dir, 'name_index.index'))
        faiss.write_index(self.tag_index, os.path.join(index_dir, 'tag_index.index'))

    def search(self, query, search_type='name', k=10):
        """Perform similarity search using FAISS indexes"""
        try:
            # Generate query embedding
            query_embedding = self.model.encode(f"query: {query}", normalize_embeddings=True)
            
            # Select appropriate index
            if search_type == 'name':
                if self.name_index is None:
                    print("Warning: Name index not loaded")
                    return []
                index = self.name_index
                # Load names from MongoDB for results
                if self.artwork_details is None:
                    artwork_details = data.get_artwork_details()
                else:
                    artwork_details = self.artwork_details
                if not artwork_details.empty:
                    items = artwork_details['display_name'].dropna().unique()
                else:
                    print("Warning: Could not load artist names from database")
                    return []
            else:  # tag search
                if self.tag_index is None:
                    print("Warning: Tag index not loaded")
                    return []
                index = self.tag_index
                # Load tags from MongoDB for results
                import data
                tag_mapping = data.get_tag_mapping()
                if not tag_mapping.empty:
                    items = tag_mapping['tag_name'].unique()
                else:
                    print("Warning: Could not load tags from database")
                    return []

            # Perform search
            D, I = index.search(query_embedding.reshape(1, -1), min(k, len(items)))
            
            # Create results
            results = [(items[i], float(score)) for i, score in zip(I[0], D[0])]
            print(f"Found {len(results)} results for query '{query}'")
            return results
        
        except Exception as e:
            print(f"Error during search: {str(e)}")
            return []

if __name__ == "__main__":
    art_search = ArtSearch() 
    prompt = "sad"
    # results = art_search.search(prompt, search_type='tag')
    results = art_search.search(prompt, search_type='tag', k=20)
    print(results)
    # print(f"Similar to {tag}:")
    # for i, (result, score) in enumerate(results[:5], 1):
    #     print(f"  {i}. {result} (Score: {score:.4f})")
