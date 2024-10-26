import pandas as pd
from openai import OpenAI
from sentence_transformers import SentenceTransformer
import numpy as np
from time import time
import os
from sklearn.cluster import AgglomerativeClustering

import dotenv
dotenv.load_dotenv()

class ExhibitionCurator:
    def __init__(self, metadata, embedding_model=SentenceTransformer('all-MiniLM-L6-v2')):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.metadata = metadata
        self.embedding_model = embedding_model
        self.descriptions = self.metadata.apply(self.get_description, axis=1)
        # print('**** Getting embeddings of descriptions ****')
        checkpoint = time()
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
        # print(f'**** Getting embeddings of descriptions done. Time taken: {time() - checkpoint} seconds ****')

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
        if use_author:
            clustering_model = AgglomerativeClustering(n_clusters=3)
        else:
            clustering_model = AgglomerativeClustering(n_clusters=None, distance_threshold=1.3)
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
        for exhibition in exhibitions:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "You are a professional art exhibition curator. You can give an accurate, straightforward, and informative description for an exhibition of artworks for the general public to understand. An exhibition can be themed based on artists, genre, style, period, color, or any other factors that are shared by the artworks in the exhibition.\nYou will be given a sentence S, and the list of artworks searched based on the sentence S (which is a list of artworks and the corresponding artists). This list of artworks should together serve as one exhibition, and you will provide more details about the exhibition. Provide a Python readable JSON string to describe the artwork with the following keys and values:\ntitle: <string, in 15 words> An elegant name for the exhibition of artworks,\ndescription: <string, in 200 words> a paragraph that introduces the themed exhibition to viewers,\ndisplay_order: <list of strings> exact same list of artwork titles provided (you should not modify the titles in any way), but reordered in a way that the new order is better for viewers to learn the exhibition. Note: You should ignore the sentence S when providing the title for exhibition (that means the exhibition title should not be simply copying keywords from the sentence S). However, your exhibition description should spend some sentences to explain how the exhibition connects with the sentence S."
                                )
                            }
                        ]
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Sentence S: {query}; list of (artwork title | artist): {exhibition}"
                            }
                        ]
                    }
                ],
                temperature=0,
                max_tokens=2048,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            responses.append(response.choices[0].message.content)
        
        exhibition_info = []
        for index, response in enumerate(responses):
            temp_df = clusters[index]
            result = response.split("\n")
            exhibition_temp = {}
            get_artworks = False
            artworks = []
            for line in result:
                if not get_artworks:
                    if "title" in line and 'titles' not in line:
                        exhibition_temp['title'] = line.split('": ')[1].replace('"', '')[:-1]
                    elif "description" in line:
                        exhibition_temp['description'] = line.split('": ')[1].replace('"', '')[:-1]
                    elif "display_order" in line or "description" in exhibition_temp:
                        get_artworks = True
                else:
                    if "]" in line and '[' not in line:
                        exhibition_temp['display_order'] = artworks
                        break
                    else:
                        artwork_id = line.split(", ")[0].replace('"', '').replace(",", "").lstrip()
                        artworks.append(artwork_id)
            if 'display_order' not in exhibition_temp:
                exhibition_temp['display_order'] = original_orders[index]
                print('Error!!!! Display order not found')
            exhibition_temp['Original_order'] = list(original_orders[index])
            ordered_ids = []
            for title in exhibition_temp['display_order']:
                matched_id = temp_df[temp_df['title'] == title]['artwork_id'].values
                if len(matched_id) == 0:
                    matched_title = process.extractOne(title, temp_df['title'].values)[0]
                    matched_id = temp_df[temp_df['title'] == matched_title]['artwork_id'].values
                ordered_ids.append(matched_id[0])
            exhibition_temp['art_pieces'] = list(ordered_ids)
            exhibition_info.append(exhibition_temp)
        return exhibition_info
