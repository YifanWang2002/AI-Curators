import os
import json
import faiss
import itertools
import numpy as np
import pandas as pd


class DescriptionSimChannel:

    def __init__(self, metadata, configs):
        self.meta_data = metadata
        self.configs = configs
        self.num_per_page = self.configs["num_per_page"]
        self.desc_embedding = np.load(self.configs["desc_emb_path"])
        self.desc_index = self.get_desc_index()
        self.desc_mapping = self.get_desc_mapping()
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
        
    def get_desc_mapping(self):
        desc_mapping = {}
        desc_count_type = pd.read_csv(self.configs["desc_count_type_path"])
        for i, row in desc_count_type.iterrows():
            desc_mapping[row["desc"]] = {"desc_no": i, "count": row["count"], "type": row["type"]}
        return desc_mapping

    def get_interacted_set(self, user_id, updated):
        # TODO: Load interacted set from the database
        if updated:
            with open(os.path.join(self.configs["interacted_dir"], f"interacted_{user_id}.txt"), "r", encoding="utf-8") as f:
                self.interacted_set = set([int(idx) for idx in f.read().splitlines()])
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

        final_recs_list = [[(sim_image[0], sim_image[1], self.exhibit_list[i]) for sim_image in filtered_recs_list[i]] for i in range(len_exhibit)]
        sorted_final_recs_list = sorted(list(itertools.chain(*final_recs_list)), key=lambda x: x[1])
        exhibit_recs_names = [f"Exhibition: {x[2]}" for x in sorted_final_recs_list]
        final_recs_list = [x[0] for x in sorted_final_recs_list]
        return final_recs_list, exhibit_recs_names, len_exhibit
    
    def __call__(self, user_id, context_info, recommended_set, default_list):
        exclude_set = self.get_interacted_set(user_id, context_info["behavior_updated"]) | recommended_set
        
        final_recs_list, exhibit_recs_names, len_exhibit = self.description_recs(default_list, exclude_set)

        return [final_recs_list], [exhibit_recs_names], len_exhibit
