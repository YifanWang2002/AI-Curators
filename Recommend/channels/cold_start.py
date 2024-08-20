import pandas as pd
import os
import ast
import re
from transformers import AutoTokenizer, AutoModel, AutoModelForMaskedLM
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import euclidean
from time import time
from sklearn.cluster import AgglomerativeClustering

class ColdStartChannel:

    def __init__(self, metadata, embedding_model = SentenceTransformer('all-MiniLM-L6-v2'), top_k = 50):
        self.user_log = None
        # Check which device pytorhc is using
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            x = torch.ones(1, device= self.device)
        else:
            self.device = torch.device("cpu")
            # print ("MPS and CUDA devices not found.")
        # print(f'Using device: {self.device}')
        # Embeddings of all images
        self.top_k = top_k
        self.embedding_model = embedding_model
        # get the tags of the artwork
        # temp_result = metadata.apply(self.get_tags_and_description, axis=1)
        self.metadata_image_names = metadata['title']
        # self.metadata_tags, self.metadata_descriptions = zip(*temp_result)
        self.metadata_tags = metadata.apply(self.get_tags, axis=1)
        # get the embeddings of the tags
        print('**** Getting embeddings of tags...')
        checkpoint = time()
        if not os.path.isfile('./Recommend/data/tag_embeddings.pt'):
            self.tag_embeddings = list(map(self.create_embeddings, self.metadata_tags))
            self.tag_embeddings = torch.stack(self.tag_embeddings)
            torch.save(self.tag_embeddings, ("./Recommend/data/tag_embeddings.pt"))
        else:
            self.tag_embeddings = torch.load("./Recommend/data/tag_embeddings.pt")
        # self.tag_embeddings = list(map(self.create_embeddings, self.metadata_tags))
        print(f'**** Getting embeddings of tags done. Time taken: {time() - checkpoint} seconds')
        # get the embeddings of the descriptions
        # print('**** Getting embeddings of descriptions...')
        # checkpoint = time()
        # self.description_embeddings = self.embedding_model.encode(self.metadata_descriptions)
        # print(f'**** Getting embeddings of descriptions done. Time taken: {time() - checkpoint} seconds')

    # a function to remove parentheses from a string
    def remove_parentheses(self,text):
        return re.sub(r'\([^)]*\)', '', text).strip()

    # a function to convert string of list to actual list
    def string_to_list(self,string):
        string = string.replace("[", "")
        string = string.replace("]", "")
        string = string.replace("'", "")
        string = string.split(", ")
        return string
    
    def get_tags(self, row):
        artist = self.remove_parentheses(row['artist_display'])
        styles = self.string_to_list(row['style_tags'])
        themes = self.string_to_list(row['theme_tags'])
        movements = self.string_to_list(row['movement'])
        tags = {
            "artists": [artist],
            "styles": styles,
            "themes": themes,
            "movements": movements
        }
        return tags
    
    # This function gets the tags and full description of the artworks in the metadata
    def get_tags_and_description(self, row):
        artist = self.remove_parentheses(row['artist_display'])
        styles = self.string_to_list(row['style_tags'])
        themes = self.string_to_list(row['theme_tags'])
        movements = self.string_to_list(row['movement'])
        tags = {
            "artists": [artist],
            "styles": styles,
            "themes": themes,
            "movements": movements
        }
        all_description = row['intro'] + '\n' + row['overview'] + '\n' + row['style'] + '\n' + row['theme']
        return tags, all_description

    # a function to get the embeddings of the artwork as the weighted embeddings of the tags
    def create_embeddings(self, object):
        artists = object['artists']
        styles = object['styles']
        themes = object['themes']
        movements = object['movements']
        #np.mean(tag_embeddings, axis=0)
        artist_embeddings = np.mean(self.embedding_model.encode(artists), axis=0)
        style_embeddings = np.mean(self.embedding_model.encode(styles), axis=0)
        theme_embeddings = np.mean(self.embedding_model.encode(themes), axis=0)
        movement_embeddings = np.mean(self.embedding_model.encode(movements), axis=0)
        # return result in a tensor and assigne to device
        results = torch.tensor(np.array([artist_embeddings, style_embeddings, theme_embeddings, movement_embeddings])).to(self.device)
        return results
    
    # calculate the similarity between two tensors using GPU with either cosine similarity, euclidean distance, or dot product
    def calculate_tensor_similarity(self, tensor1, tensor2, method = 'cosine'):
        if method == 'cosine':
            result =  torch.nn.functional.cosine_similarity(tensor1, tensor2).cpu().detach().numpy()
        elif method == 'euclidean':
            result =  - (torch.nn.functional.pairwise_distance(tensor1, tensor2, p=1).cpu().detach().numpy())
        else:
            result = np.array([torch.dot(tensor1[i], tensor2[i]).cpu().detach().numpy() for i in range(len(tensor1))])
            # for row1, row2 in zip(tensor1, tensor2):
            #     dot_product = row1@row2
            #     result.append(dot_product)
        # print(result.shape)
        return np.average(result, weights = [0.1, 0.3, 0.3, 0.3], axis=0)

    # find the top k most similar artworks to the new user
    def get_top_k_similar_artworks(self, user_embeddings, artwork_embeddings, k, method = 'dot'):
        results = []
        for i, artwork in enumerate(artwork_embeddings):
            similarity = self.calculate_tensor_similarity(user_embeddings, artwork, method)
            results.append((i, similarity))
        results = sorted(results, key=lambda x: x[1], reverse=True)
        return results[:k]

    def update_data(self, new_user_log):
        if self.user_log is not None and self.user_log == new_user_log:
            print('Error! User log is the same as the previous one.')
        self.user_log = new_user_log
        self.user_embeddings = self.create_embeddings(self.user_log)

    def get_recs_list(self):
        self.top_k_result = self.get_top_k_similar_artworks(self.user_embeddings, self.tag_embeddings, self.top_k)

    # def get_top_k_cluster(self):
    #     indices = [i for i, _ in self.top_k_result]
    #     image_list = [self.metadata_image_names[i] for i, _ in self.top_k_result]
    #     top_k_description_embeddings = [self.description_embeddings[i] for i in indices]
    #     clustering_model = AgglomerativeClustering(
    #         n_clusters=None, distance_threshold=1.3
    #     )  # , affinity='cosine', linkage='average', distance_threshold=0.4)
    #     clustering_model.fit(top_k_description_embeddings)
    #     cluster_assignment = clustering_model.labels_
    #     self.top_k_df = pd.DataFrame(zip(indices, image_list, cluster_assignment), columns=['index', 'title', 'cluster_label'])

    def __call__(self):
        self.get_recs_list()
        indices = [i for i, _ in self.top_k_result]
        # self.get_top_k_cluster()
        return indices
