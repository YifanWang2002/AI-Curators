import os
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
import torch
import pickle

class ArtSearch:
    def __init__(self, data_dir="../data", use_precomputed=True):
        self.data_dir = data_dir
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
        df_names = pd.read_csv(os.path.join(self.data_dir, 'dimension_tables', 'dim_artwork.csv'))
        self.artist_names = (df_names['artist_given_name'] + ' ' + df_names['artist_family_name']).dropna().unique()

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
        
        # Load the data first to get the arrays in correct order
        self.load_data()
        
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
        query_embedding = self.model.encode(f"query: {query}", normalize_embeddings=True)
        index = self.name_index if search_type == 'name' else self.tag_index
        items = self.artist_names if search_type == 'name' else self.tags
        D, I = index.search(query_embedding.reshape(1, -1), k)
        scores = D[0]
        # creates a list of tuples (item, score)
        results = [(items[i], float(score)) for i, score in zip(I[0], scores)]
        return results

if __name__ == "__main__":
    art_search = ArtSearch() 
    prompt = "sad"
    # results = art_search.search(prompt, search_type='tag')
    results = art_search.search(prompt, search_type='tag', k=20)
    print(results)
    # print(f"Similar to {tag}:")
    # for i, (result, score) in enumerate(results[:5], 1):
    #     print(f"  {i}. {result} (Score: {score:.4f})")
