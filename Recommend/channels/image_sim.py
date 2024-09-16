import os
import faiss
import random
import numpy as np


class ImageSimChannel:

    def __init__(self, configs):
        # Embeddings of all images
        self.configs = configs
        self.embeddings = np.load(self.configs["image_emb_path"])
        self.num_per_page = self.configs["num_per_page"]
        self.shuffle_len = self.configs["shuffle_len"]

        self.index = faiss.read_index(self.configs["image_emb_index_path"])
        self.image_list = []
        self.interacted_set = set()

    def update_data(self, unique_log, num_image, interacted_set):
        self.image_list = unique_log.head(num_image).index.values
        self.interacted_set = interacted_set
    
    def get_interacted_set(self, user_id, updated):
        # TODO: Load interacted set from the database
        if updated:
            with open(os.path.join(self.configs["interacted_dir"], f"interacted_{user_id}.txt"), "r", encoding="utf-8") as f:
                self.interacted_set = set(f.read().splitlines())
        return self.interacted_set

    def get_recs_list(self, object_ids, num_rec_per_image):
        image_embeddings = self.embeddings[object_ids]
        D, I = self.index.search(image_embeddings, num_rec_per_image)
        return I[:, 1:].tolist()

    def __call__(self, user_id, context_info, recommended_set, default_list):
        exclude_set = self.get_interacted_set(user_id, context_info["behavior_updated"]) | recommended_set

        num_rec = self.num_per_page * 2

        if len(self.image_list) == 0:
            self.image_list = default_list

        recs_list = self.get_recs_list(self.image_list, num_rec)
        filtered_recs_list = [
            [x for x in recs if x not in exclude_set] for recs in recs_list
        ]
        while any(len(recs) < self.num_per_page for recs in filtered_recs_list):
            num_rec += self.num_per_page
            recs_list = self.get_recs_list(self.image_list, num_rec)
            filtered_recs_list = [
                [x for x in recs if x not in exclude_set] for recs in recs_list
            ]

        final_recs_list = [
            random.sample(recs[: self.shuffle_len], self.shuffle_len)
            + recs[self.shuffle_len : self.num_per_page]
            for recs in filtered_recs_list
        ]

        image_names = [f"Image: {x}" for x in self.image_list]
        print(image_names)
        return final_recs_list, image_names, len(final_recs_list)
