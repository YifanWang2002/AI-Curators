import pandas as pd
from openai import OpenAI
from sentence_transformers import SentenceTransformer
import numpy as np
from time import time
import os
from pydantic import BaseModel
from typing import List
from k_means_constrained import KMeansConstrained

import dotenv
dotenv.load_dotenv()

class ExhibitionResponse(BaseModel):
    title: str
    description: str

class ExhibitionCurator:
    def __init__(self, metadata, embedding_model=SentenceTransformer('all-MiniLM-L6-v2')):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.metadata = metadata
        self.embedding_model = embedding_model
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
        min_size = total_items // 3
        max_size = min_size + 1
        
        # Initialize KMeansConstrained with size constraints
        clustering_model = KMeansConstrained(
            n_clusters=3,
            size_min=min_size,
            size_max=max_size,
            random_state=42
        )
        
        clustering_model.fit(top_k_description_embeddings)
        
        # Use loc to set values
        recommendation_df.loc[:, 'cluster_label'] = clustering_model.labels_
        recommendation_df = recommendation_df[['artwork_id', 'title', 'display_name', 'cluster_label']]
        
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
        
        system_prompt = """You are a distinguished museum curator with expertise in fine art and exhibition design. Your curatorial approach emphasizes creating meaningful connections between artworks while making art accessible to diverse audiences.

        Given a visitor's interest (expressed through their query) and a selection of artworks, your task is to:

        1. Create an exhibition title (15 words maximum):
        - Craft an evocative yet precise title that captures the exhibition's conceptual framework
        - Avoid generic descriptors; use specific, meaningful language
        - Consider cultural and historical resonance
        
        2. Write a curatorial introduction (200 words maximum) that:
        - Establishes the exhibition's intellectual and aesthetic framework
        - Illuminates thematic connections across the selected works
        - Contextualizes the exhibition within broader artistic or cultural movements
        - Addresses the visitor's expressed interests while expanding their perspective
        - Considers formal elements (color, composition, technique) alongside conceptual themes
        - Highlights unexpected dialogues between works from different periods or styles
        - Emphasizes experiential aspects of encountering these works together
        
        Key curatorial principles:
        - Focus on thematic resonance rather than chronological progression
        - Draw sophisticated connections while remaining accessible
        - Balance historical context with contemporary relevance
        - Consider spatial and visual relationships between works
        - Acknowledge both aesthetic and conceptual dimensions
        - Create an engaging narrative that invites deeper exploration
        
        Your writing should be:
        - Scholarly yet approachable
        - Rich in insight without being verbose
        - Confident in artistic interpretation
        - Free of jargon while maintaining intellectual depth
        
        Avoid:
        - Listing artwork titles mechanically
        - Overly biographical artist details
        - Chronological cataloguing
        - Generic art historical phrases
        - Technical terminology without context
        """.strip()

        for index, exhibition in enumerate(exhibitions):  # Add index to the loop
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
                    response_format=ExhibitionResponse
                )
                response = completion.choices[0].message.parsed
                temp_df = clusters[index]
                
                # Simplified exhibition creation
                exhibition_temp = {
                    'exhibition_id': index,
                    'title': response.title,
                    'description': response.description,
                    'art_pieces': list(grouped_ids[index]),  # Use original order directly
                    'curator_id': index,
                    'pieces_count': len(grouped_ids[index])
                }
                
                responses.append(exhibition_temp)
            except Exception as e:
                print(f"Error processing exhibition: {e}")
                # Fallback to original order if parsing fails
                exhibition_temp = {
                    'exhibition_id': index,
                    'title': 'Untitled Exhibition',
                    'description': 'Exhibition details unavailable',
                    'art_pieces': list(grouped_ids[index]),
                    'curator_id': index,
                    'pieces_count': len(grouped_ids[index]),
                }
                responses.append(exhibition_temp)
        
        return responses
