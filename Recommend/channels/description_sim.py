import os
import json
import faiss
import itertools
import numpy as np
import pandas as pd
from Recommend.api.data import get_clicked_exhibitions_by_user


class DescriptionSimChannel:

    def __init__(self, configs):
        self.configs = configs
        self.num_per_page = self.configs["num_per_page"]
        self.desc_embedding = np.load(self.configs["desc_emb_path"])
        self.desc_index = self.get_desc_index()
        self.interacted_set = set()
        self.exhibit_list = []

    def get_desc_index(self):
        if os.path.exists(self.configs["desc_emb_index_path"]):
            return faiss.read_index(self.configs["desc_emb_index_path"])
        else:
            desc_index = faiss.IndexFlatL2(self.desc_embedding.shape[1])
            desc_index.add(self.desc_embedding)
            faiss.write_index(desc_index, self.configs["desc_emb_index_path"])
            return desc_index

    def get_interacted_set(self, user_id, updated):
        if updated:
            records = get_clicked_exhibitions_by_user(user_id)
            if records and records["status"] == "success":
                # TODO: Analyze the ratio of interaction and decide how to update the interacted set
                self.interacted_set = self.interacted_set | set([idx["exhibition_id"] for idx in records["data"]])
        return self.interacted_set
    
    def get_recs_list_by_descs(self, exhibit_ids, num_per_desc_type):
        desc_embeddings = self.desc_embedding[exhibit_ids]
        D, I = self.desc_index.search(desc_embeddings, num_per_desc_type)
        recs_list = []
        for i in range(len(I)):
            recs_list.append([(I[i, j], D[i, j]) for j in range(len(I[i])) if j != 0])
        return recs_list

    def description_recs(self, default_list, exclude_set):
        num_rec = self.num_per_page * 2

        if len(self.exhibit_list) == 0:
            self.exhibit_list = default_list
        
        len_exhibit = len(self.exhibit_list)
        recs_list = self.get_recs_list_by_descs(self.exhibit_list, num_rec)
        filtered_recs_list = [
            [x for x in recs if x[0] not in exclude_set] for recs in recs_list
        ]
        while any(len(recs) < self.num_per_page for recs in filtered_recs_list):
            num_rec += self.num_per_page
            recs_list = self.get_recs_list_by_descs(self.exhibit_list, num_rec)
            filtered_recs_list = [
                [x for x in recs if x[0] not in exclude_set] for recs in recs_list
            ]

        final_recs_list = [[(int(sim_exhibit[0]), sim_exhibit[1], self.exhibit_list[i]) for sim_exhibit in filtered_recs_list[i]] for i in range(len_exhibit)]
        sorted_final_recs_list = sorted(list(itertools.chain(*final_recs_list)), key=lambda x: x[1])
        exhibit_recs_names = [f"Description: {x[2]}" for x in sorted_final_recs_list]
        final_recs_list = [x[0] for x in sorted_final_recs_list]
        return final_recs_list, exhibit_recs_names, len_exhibit
    
    def __call__(self, user_id, context_info, recommended_set, default_list):
        exclude_set = self.get_interacted_set(user_id, context_info["behavior_updated"]) | recommended_set
        
        final_recs_list, exhibit_recs_names, len_exhibit = self.description_recs(default_list, exclude_set)

        return [final_recs_list], [exhibit_recs_names], int(len_exhibit)
