import os
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
import torch

class ArtSearch:
    def __init__(self, data_dir="../new_data"):
        self.data_dir = data_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Load E5 model
        self.model = SentenceTransformer("intfloat/e5-large-v2").to(self.device)

        # Load artist names and tags
        self.load_data()

        # Create indexes
        self.create_indexes()

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

    def search(self, query, search_type='name', k=10):
        query_embedding = self.model.encode(f"query: {query}", normalize_embeddings=True)
        index = self.name_index if search_type == 'name' else self.tag_index
        items = self.artist_names if search_type == 'name' else self.tags
        D, I = index.search(query_embedding.reshape(1, -1), k)
        
        # # convert cosine similarities to probability-like scores
        # scores = (D[0] + 1) / 2  # Map from [-1, 1] to [0, 1]
        
        # # normalize scores so they sum to 1
        # scores = scores / np.sum(scores)

        scores = D[0]
        
        # create a list of tuples (item, score)
        results = [(items[i], float(score)) for i, score in zip(I[0], scores)]
        
        return results

