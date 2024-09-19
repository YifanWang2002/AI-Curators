import pandas as pd
from openai import OpenAI
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
from time import time
import os
from sklearn.cluster import AgglomerativeClustering

class ExhibitionCurator:
    def __init__(self, api_key, metadata, embedding_model = SentenceTransformer('all-MiniLM-L6-v2')):
        # Check which device pytorhc is using
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            x = torch.ones(1, device= self.device)
        else:
            self.device = torch.device("cpu")
        self.client = OpenAI(api_key=api_key)
        self.metadata = metadata
        self.embedding_model = embedding_model
        self.descriptions = self.metadata.apply(self.get_description, axis=1)
        # get the embeddings of the descriptions
        print('**** Getting embeddings of descriptions...')
        # self.description_embeddings = self.embedding_model.encode(self.descriptions)
        checkpoint = time()
        if not os.path.isfile('./data/description_embeddings.npy'):
            self.description_embeddings = self.embedding_model.encode(self.descriptions)
            self.description_embeddings = torch.tensor(self.description_embeddings).to('cpu')
            torch.save(self.description_embeddings, ('./data/description_embeddings.pt'))
        else:
            self.description_embeddings = torch.load('./data/description_embeddings.pt')
        print(f'**** Getting embeddings of descriptions done. Time taken: {time() - checkpoint} seconds')

    def get_description(self, row):
        all_description = str(row['intro']) + '\n' + str(row['overview']) + '\n' + str(row['style']) + '\n' + str(row['theme'])
        return all_description
    
    def get_exhibitions(self, recommendations):
        indices = recommendations.index
        recommendation_df = self.metadata.iloc[indices]
        # image_list = self.recommendations['image_id'].values
        # top_k_description_embeddings = [self.description_embeddings[i] for i in indices]
        top_k_description_embeddings = self.description_embeddings[indices]
        clustering_model = AgglomerativeClustering(
            n_clusters=None, distance_threshold=1.3
        )  # , affinity='cosine', linkage='average', distance_threshold=0.4)
        clustering_model.fit(top_k_description_embeddings)
        cluster_assignment = clustering_model.labels_
        recommendation_df['cluster_label'] = cluster_assignment
        recommendation_df = recommendation_df[['artwork_id','title', 'display_name', 'cluster_label']]
        exhibitions = []
        # clusters = []
        grouped_ids = []
        for cluster_id in recommendation_df['cluster_label'].unique():
            cluster = recommendation_df[recommendation_df['cluster_label'] == cluster_id]
            exhibition = ""
            for index, row in cluster.iterrows():
                exhibition += str(row['artwork_id']) + " | " + str(row['title']) + " | " + str(row['display_name']) + "; "
            exhibitions.append(exhibition[:-2])
            grouped_ids.append(cluster['artwork_id'].values)
            # clusters.append(cluster)
        return exhibitions, grouped_ids
    
    def curate(self, recommendations):
        responses = []
        exhibitions, grouped_ids = self.get_exhibitions(recommendations)
        for exhibition in exhibitions:
            response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                "role": "system",
                "content": [
                    {
                    "type": "text",
                    "text": "You are a professional art exhibition curator.  You can give an accurate, straightforward, and informative description for an exhibition of artworks for the general public to understand. An exhibition can be themed based on artists, genre, style, period, color, or any other factors that are shared by the artworks in the exhibition.\nYou will be given a list of artwork ID, artwork titles and the corresponding artists. Provide a Python readable JSON string to describe the artwork with the following keys and values:\ntitle: <string, in 15 words> An elegant name for the exhibition of artworks,\ndescription: <string, in 200 words> a paragraph that introduces the themed exhibition to viewers,\nartworks_ids_in_order: <list of strings, ordered> rearrange the order of the input list of artworks ID such that the new order is better for viewers to learn the exhibition."
                    }
                ]
                },
                {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": f"list of (artwork ID | artwork title | artist): {exhibition}"
                    }
                ]
                }  
            ],
            temperature=0,
            max_tokens=1024,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
            )
            responses.append(response)
        
        exhibition_info = []
        for index, response in enumerate(responses):
            result = response.choices[0].message.content.split("\n")
            exhibition_temp = {}
            get_artworks = False
            artworks = []
            for line in result:
                if not get_artworks:
                    if "title" in line and 'titles' not in line:
                        exhibition_temp['title'] = line.split('": ')[1].replace('"', '')[:-1]
                    elif "description" in line:
                        exhibition_temp['description'] = line.split('": ')[1].replace('"', '')[:-1]
                    elif "artworks_ids_in_order" in line:
                        get_artworks = True
                else:
                    if "]" in line and '[' not in line:
                        exhibition_temp['art_pieces'] = artworks
                        break
                    else:
                        artwork_id = line.split(", ")[0]
                        artwork_id = artwork_id.replace('"', '').replace(",", "").lstrip()
                        artworks.append(artwork_id)
            if 'art_pieces' not in exhibition_temp:
                exhibition_temp['art_pieces'] = grouped_ids[index]

                print('Error! Incomplete')
            exhibition_info.append(exhibition_temp)
        return exhibition_info
