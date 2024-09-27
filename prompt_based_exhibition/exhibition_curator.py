import pandas as pd
from openai import OpenAI
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
from time import time
import os
from sklearn.cluster import AgglomerativeClustering
from fuzzywuzzy import process

# Function to see if x is a match of target
def get_matches(target, x, threshold = 90):
    ratio = process.extractOne(target, x)
    return ratio[1] >= threshold

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
        if not os.path.isfile(r'D:\Metaverse_Museum\AI-Curators\data\description_embeddings.pt'):
            print('Embeddings not found. Generating...')
            self.description_embeddings = self.embedding_model.encode(self.descriptions)
            self.description_embeddings = torch.tensor(self.description_embeddings).to('cpu')
            torch.save(self.description_embeddings, (r'D:\Metaverse_Museum\AI-Curators\data\description_embeddings.pt'))
        else:
            print("Loading embeddings from file...")
            self.description_embeddings = torch.load(r'D:\Metaverse_Museum\AI-Curators\data\description_embeddings.pt')
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
        recommendation_df.loc[:,'cluster_label'] = cluster_assignment
        recommendation_df = recommendation_df[['artwork_id','title', 'display_name', 'cluster_label']]
        exhibitions = []
        # clusters = []
        grouped_ids = []
        original_orders = []
        clusters = []
        for cluster_id in recommendation_df['cluster_label'].unique():
            cluster = recommendation_df[recommendation_df['cluster_label'] == cluster_id]
            exhibition = ""
            for index, row in cluster.iterrows():
                exhibition += str(row['title']) + " | " + str(row['display_name']) + "; "
            exhibitions.append(exhibition[:-2])
            grouped_ids.append(cluster['artwork_id'].values)
            original_orders.append(cluster['title'].values)
            clusters.append(cluster.copy())
            # clusters.append(cluster)
        return exhibitions, grouped_ids, original_orders, clusters
    
    def curate(self, recommendations, query):
        responses = []
        exhibitions, grouped_ids, original_orders, clusters = self.get_exhibitions(recommendations)
        for exhibition in exhibitions:
            response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                "role": "system",
                "content": [
                    {
                    "type": "text",
                    "text": "You are a professional art exhibition curator. You can give an accurate, straightforward, and informative description for an exhibition of artworks for the general public to understand. An exhibition can be themed based on artists, genre, style, period, color, or any other factors that are shared by the artworks in the exhibition.\nYou will be given a sentence S, and the list of artworks searched based on the sentence S (which is a list of artworks and the corresponding artists). This list of artworks should together serve as one exhibition, and you will provide more details about the exhibition. Provide a Python readable JSON string to describe the artwork with the following keys and values:\ntitle: <string, in 15 words> An elegant name for the exhibition of artworks,\ndescription: <string, in 200 words> a paragraph that introduces the themed exhibition to viewers,\ndisplay_order: <list of strings> exact same list of artwork titles provided (you should not modify the titles in any way), but reordered in a way that the new order is better for viewers to learn the exhibition. Note: You should ignore the sentence S when providing the title for exhibition (that means the exhibition title should not be simply copying keywords from the sentence S). However, your exhibition description should spend some sentences to explain how the exhibition connects with the sentence S."
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
                        artwork_id = line.split(", ")[0]
                        artwork_id = artwork_id.replace('"', '').replace(",", "").lstrip()
                        artworks.append(artwork_id)
            if 'display_order' not in exhibition_temp:
                exhibition_temp['display_order'] = original_orders[index]

                print('Error!!!! Display order not found')
            exhibition_temp['Original_order'] = list(original_orders[index])
            ordered_ids = []
            for title in exhibition_temp['display_order']:
                # for i in reversed(range(len(title))):
                #     if i < len(title) - 1:
                #         print('Matching issue: try partial match')
                #     matched_id = temp_df[temp_df['title'].str.contains(r'{}'.format(title[:i]))]['artwork_id'].values
                #     if len(matched_id) > 0:
                #         matched_id = matched_id[0]
                #         break
                matched_id = temp_df[temp_df['title'] == title]['artwork_id'].values
                if len(matched_id) == 0:
                    # use fuzzy matching, with threshold of 90, and get the best match
                    matched_title = process.extractOne(title, temp_df['title'].values)[0]
                    matched_id = temp_df[temp_df['title'] == matched_title]['artwork_id'].values

                ordered_ids.append(matched_id[0])
            exhibition_temp['art_pieces'] = list(ordered_ids)
            exhibition_info.append(exhibition_temp)
        return exhibition_info
