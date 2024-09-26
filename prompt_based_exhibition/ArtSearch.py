import os
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
import torch
import pickle
class ArtSearch:
    def __init__(self, data_dir="../new_data", use_precomputed=True):
        self.data_dir = data_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Load E5 model
        self.model = SentenceTransformer("intfloat/e5-large-v2").to(self.device)

        if use_precomputed:
            self.load_precomputed_data()
        else:
            self.load_data()
            self.create_indexes()
            self.save_precomputed_data()

    def load_data(self):
        df_names = pd.read_csv(os.path.join(self.data_dir, 'artwork_with_tags.csv'))
        self.artist_names = (df_names['artist_given_name'] + ' ' + df_names['artist_family_name']).dropna().unique()

        df_tags = pd.read_csv(os.path.join(self.data_dir, 'tag_count_type.csv'))
        self.tags = df_tags['tag'].dropna().unique()

    def create_indexes(self):
        self.name_index = self.create_index(self.artist_names)
        self.tag_index = self.create_index(self.tags)

    def create_index(self, items):
        embeddings = self.model.encode(items, normalize_embeddings=True)
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        return index
    
    def load_precomputed_data(self):
        with open(os.path.join(self.data_dir, 'art_search_indexes.pkl'), 'rb') as f:
            data = pickle.load(f)
        self.artist_names = data['artist_names']
        self.tags = data['tags']
        self.name_index = data['name_index']
        self.tag_index = data['tag_index']

    def save_precomputed_data(self):
        data = {
            'artist_names': self.artist_names,
            'tags': self.tags,
            'name_index': self.name_index,
            'tag_index': self.tag_index
        }
        with open(os.path.join(self.data_dir, 'art_search_indexes.pkl'), 'wb') as f:
            pickle.dump(data, f)

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
    art_search = ArtSearch() # default use_precomputed=True to use the cache data
    tag = 'colorful'
    results = art_search.search(tag, search_type='tag')
    print(f"Similar to {tag}:")
    for i, (result, score) in enumerate(results[:5], 1):
        print(f"  {i}. {result} (Score: {score:.4f})")