import os
from time import time
from typing import List

import dotenv
import numpy as np
import pandas as pd
from k_means_constrained import KMeansConstrained
from sklearn.cluster import AgglomerativeClustering
from openai import OpenAI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

dotenv.load_dotenv()

class ExhibitionResponse(BaseModel):
    title: str
    description: str

class ExhibitionCurator:
    def __init__(self, metadata, embedding_model=SentenceTransformer('all-MiniLM-L6-v2'), start_id=0, curator_id=0):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.metadata = metadata
        self.embedding_model = embedding_model
        self.start_id = start_id
        self.curator_id = curator_id
        self.descriptions = self.metadata.apply(self.get_description, axis=1)
        # print('**** Getting embeddings of descriptions ****')
        embeddings_path = os.path.join(os.getcwd(), 'data', 'index_files', 'description_embeddings.npy')
        if not os.path.isfile(embeddings_path):
            print('Embeddings not found. Generating...')
            self.description_embeddings = self.embedding_model.encode(self.descriptions)
            np.save(embeddings_path, self.description_embeddings)
        else:
            print("Loading embeddings from file...")
            loaded_embeddings = np.load(embeddings_path)
            # Validate embeddings shape matches metadata
            if len(loaded_embeddings) != len(self.metadata):
                raise ValueError(f"Loaded embeddings shape ({len(loaded_embeddings)}) doesn't match metadata length ({len(self.metadata)})")
            self.metadata['embedding'] = loaded_embeddings.tolist()
            self.description_embeddings = loaded_embeddings

    def get_description(self, row):
        all_description = f"{row['intro']}\n{row['overview']}\n{row['style']}\n{row['theme']}"
        return all_description

    def get_exhibitions(self, recommendations, use_author=False):
        indices = recommendations['index']
        recommendation_df = recommendations.copy()
        # Left join with metadata to get embeddings
        merged_df = recommendation_df.merge(self.metadata[['artwork_id', 'embedding']], on='artwork_id', how='left')
        # Get embeddings from metadata using indices
        top_k_description_embeddings = np.stack(merged_df['embedding'].values)
        
        # Calculate cluster sizes based on total number of items
        total_items = len(top_k_description_embeddings)
        min_size = 5

        if total_items < 10:
            n_clusters = 1
        elif total_items >= 10 and total_items < 15:
            n_clusters = 2
        else:
            n_clusters = 3
        
        if n_clusters == 1:
            labels = 0
        elif n_clusters == 2:
            # Initialize KMeansConstrained with size constraints
            clustering_model = KMeansConstrained(
                n_clusters=2,
                size_min=min_size,
                random_state=42
            )
            
            clustering_model.fit(top_k_description_embeddings)
            labels = clustering_model.labels_
        else:
            clustering_model = AgglomerativeClustering(n_clusters=None, distance_threshold=1.3)
            labels = clustering_model.fit_predict(top_k_description_embeddings)

            # check cluster sizes
            clusters = {label: np.where(labels == label)[0] for label in np.unique(labels)}

            # Post-process small clusters
            for cluster_label, indices in clusters.items():
                if len(indices) < min_size:
                    # find the nearest larger cluster
                    cluster_centroids = {l: top_k_description_embeddings[clusters[l]].mean(axis=0) for l in clusters if 
                                         len(clusters[l] >= min_size)}
                    nearest_cluster = min(cluster_centroids.keys(), key = lambda l: 
                                          np.linalg.norm(top_k_description_embeddings[indices].mean(axis=0) - cluster_centroids[l]))
                    labels[indices] = nearest_cluster

        # Use loc to set values
        recommendation_df.loc[:, 'cluster_label'] = labels
        recommendation_df = recommendation_df[['artwork_id', 'title', 'display_name', 'cluster_label']]
        
        # remove rows with cluster_label larger than 2
        recommendation_df = recommendation_df[recommendation_df['cluster_label'] < 3]
        
        exhibitions = []
        grouped_ids = []
        original_orders = []
        clusters = []
        for cluster_id in recommendation_df['cluster_label'].unique():
            cluster = recommendation_df[recommendation_df['cluster_label'] == cluster_id].copy()  # Make explicit copy
            exhibition = "; ".join([f"{row['title']} | {row['display_name']}" for index, row in cluster.iterrows()])
            exhibitions.append(exhibition)
            grouped_ids.append(cluster['artwork_id'].values)
            original_orders.append(cluster['title'].values)
            clusters.append(cluster)
            
        return exhibitions, grouped_ids, original_orders, clusters

    def curate(self, recommendations: pd.DataFrame, query: str, use_author=False) -> list[dict]:
        responses = []
        exhibitions, grouped_ids, original_orders, clusters = self.get_exhibitions(recommendations, use_author)
        
        system_prompt = """You are a professional art exhibition curator. 
        You give accurate, straightforward, and informative descriptions for art exhibitions that help the general public understand and connect with the artworks.
        You curate exhibitions based on artists, genre, style, period, color, or any shared characteristics among the artworks.
        
        You are given a user query and a list of artworks and their artists.
        Your task is to provide:
        1. an exhibition title (15 words max): Create an elegant name that captures the exhibition's essence
        2. a description (1 or 2 paragraphs, in total 100 words max): Craft an engaging introduction that:
            - introduces the exhibition's theme and significance
            - weaves together the artworks' thematic connections
            - mentions key pieces naturally without chronological references
            - explains how the collection responds to the user's query
            
        Write in a warm, inviting tone that focuses on themes and connections rather than sequence.
        Note: 1. Do not mention any individual artwork names in the exhibitition title;
                2. Unless the user query is about a specific artist, do not mention any artist names in the description;
                3. In your description, do not focus too much on any single artwork or artist, but instead focus on all the artworks as a collection, and describe more the similarities and connections between them.
        
        An example exhibition from the Met Museum:
        Title: "Look Again: European Paintings 1300–1800"
        Description: "The reopened galleries dedicated to European Paintings from 1300 to 1800 highlight fresh narratives and dialogues among more than 700 works of art from the Museum’s world-famous holdings. The newly reconfigured galleries—which include recently acquired paintings and prestigious loans, as well as select sculptures and decorative art—will showcase the interconnectedness of cultures, materials, and moments across The Met collection.
        The chronologically arranged galleries will feature longstanding strengths of the collection—such as masterpieces by Jan van Eyck, Caravaggio, and Poussin; the most extensive collection of 17th-century Dutch art in the western hemisphere; and the finest holdings of El Greco and Goya outside Spain—while also giving renewed attention to women artists, exploring Europe’s complex relationships with New Spain and the Viceroyalty of Peru, and looking more deeply into histories of class, gender, race, and religion."
        """.strip()

        for index, exhibition in enumerate(exhibitions):
            try:
                completion = self.client.beta.chat.completions.parse(
                    model="gpt-4o-mini", 
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": f"Sentence S: {query}; list of (artwork title | artist): {exhibition}"
                        }
                    ],
                    temperature=0.6,
                    response_format=ExhibitionResponse
                )
                response = completion.choices[0].message.parsed
                temp_df = clusters[index]
                
                # Simplified exhibition creation
                exhibition_temp = {
                    'exhibition_id': self.start_id + index,
                    'title': response.title,
                    'description': response.description,
                    'art_pieces': [str(artwork_id) for artwork_id in grouped_ids[index]],
                    'curator_id': str(self.curator_id),
                    'pieces_count': len(grouped_ids[index])
                }
                
                responses.append(exhibition_temp)
            except Exception as e:
                print(f"Error processing exhibition: {e}")
                # Fallback with real exhibition ID
                exhibition_temp = {
                    'exhibition_id': self.start_id + index,
                    'title': 'Untitled Exhibition',
                    'description': 'Exhibition details unavailable',
                    'art_pieces': list(grouped_ids[index]),
                    'curator_id': self.curator_id,
                    'pieces_count': len(grouped_ids[index]),
                }
                responses.append(exhibition_temp)
        
        return responses