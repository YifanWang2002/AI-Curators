import os
import json
import faiss
import itertools
import numpy as np
import pandas as pd
from api.data import get_clicked_artworks_by_user, get_clicked_exhibitions_by_user, get_all_tags, get_artworks_by_tag_id, get_exhibitions_by_tag_id
from api.data import get_tag_preferences_by_user


class UserProfileChannel:

    def __init__(self, user_id, configs):
        self.user_id = user_id
        self.configs = configs
        self.num_per_page = self.configs["num_per_page"]
        self.tag_embedding = np.load(self.configs["tag_emb_path"])
        self.tag_index = self.get_tag_index()
        self.tag_name2id_mapping = self.get_tag_mapping()
        self.tag_prefernece_ids = get_tag_preferences_by_user(user_id)
        self.interacted_set = set()

    def get_tag_index(self):
        if os.path.exists(self.configs["tag_emb_index_path"]):
            return faiss.read_index(self.configs["tag_emb_index_path"])
        else:
            tag_index = faiss.IndexFlatL2(self.tag_embedding.shape[1])
            tag_index.add(self.tag_embedding)
            faiss.write_index(tag_index, self.configs["tag_emb_index_path"])
            return tag_index
        
    def get_tag_mapping(self):
        tag_name2id_mapping = {}
        data = get_all_tags()
        if not data or data["status"] != "success":
            return tag_name2id_mapping
        for tag in data["data"]:
            tag_name2id_mapping[tag["tag_name"]] = {"tag_id": tag["tag_id"], "count": tag["count"], "type": tag["tag_type"]}
        return tag_name2id_mapping

    def get_interacted_set(self, user_id, updated):
        if updated:
            if self.configs["object_type"] == "artwork":
                records = get_clicked_artworks_by_user(user_id)
                id_key = "artwork_id"
            elif self.configs["object_type"] == "exhibition":
                records = get_clicked_exhibitions_by_user(user_id)
                id_key = "exhibition_id"
            else:
                raise ValueError(f"Invalid object type: {self.configs['object_type']}")
            if records and records["status"] == "success":
                # TODO: Analyze the ratio of interaction and decide how to update the interacted set
                self.interacted_set = self.interacted_set | set([idx[id_key] for idx in records["data"]])
        return self.interacted_set
    
    def get_recs_list_by_tags(self, num_per_tag_type):
        if len(self.tag_prefernece_ids) == 0:
            return [set()]
        tag_embeddings = self.tag_embedding[self.tag_prefernece_ids]
        D, I = self.tag_index.search(tag_embeddings, num_per_tag_type)
        recs_tag_list = []
        for i in range(len(I)):
            recs_tag_list.append([(I[i, j], D[i, j]) for j in range(len(I[i])) if j != 0])
        recs_object_list = []
        for i, recs in enumerate(recs_tag_list):
            object_recs = set()
            for x in recs:
                if self.configs["object_type"] == "artwork":
                    data = get_artworks_by_tag_id(x[0])
                elif self.configs["object_type"] == "exhibition":
                    data = get_exhibitions_by_tag_id(x[0])
                else:
                    raise ValueError(f"Invalid object type: {self.configs['object_type']}")
                if data and data["status"] == "success":
                    object_recs.update(data["data"])
            recs_object_list.append(object_recs)
        return recs_object_list
    
    def personalized_tags_recs(self, exclude_set):
        num_per_tag_type = self.num_per_page
        recs_list = self.get_recs_list_by_tags(num_per_tag_type)
        filtered_recs_list = [
            list(recs.difference(exclude_set)) for recs in recs_list
        ]
        iteration = 0
        while sum(len(recs) < self.num_per_page for recs in filtered_recs_list) == len(self.tag_prefernece_ids) and iteration < 5:
            num_per_tag_type += self.num_per_page
            recs_list = self.get_recs_list_by_tags(num_per_tag_type)
            filtered_recs_list = [
                list(recs.difference(exclude_set)) for recs in recs_list
            ]
            iteration += 1
        recs_hash = {}
        for i, x in enumerate(self.tag_prefernece_ids):
            recs_hash.update({k: f"Profile Tag: {x}" for k in filtered_recs_list[i]})
        return list(recs_hash.keys()), list(recs_hash.values()), len(recs_hash)
    
    def personalized_queries_recs(self, exclude_set):
        return [], [], 0
    
    def __call__(self, context_info, recommended_set):
        exclude_set = self.get_interacted_set(self.user_id, context_info["behavior_updated"]) | recommended_set
        
        tags_recs_list, tags_recs_names, len_tags = self.personalized_tags_recs(exclude_set)
        queries_recs_list, queries_recs_names, len_queries = self.personalized_queries_recs(exclude_set)
        return [tags_recs_list], [tags_recs_names], len_tags
