import os
import faiss
import random
import itertools
import numpy as np


class ImageSimChannel:

    def __init__(self, configs):
        # Embeddings of all images
        self.configs = configs
        self.image_embedding = np.load(self.configs["image_emb_path"])
        self.num_per_page = self.configs["num_per_page"]
        self.shuffle_len = self.configs["shuffle_len"]

        self.index = self.get_image_index()
        self.image_list = []
        self.interacted_set = set()
    
    def get_image_index(self):
        if os.path.exists(self.configs["image_emb_index_path"]):
            return faiss.read_index(self.configs["image_emb_index_path"])
        else:
            image_index = faiss.IndexFlatL2(self.image_embedding.shape[1])
            image_index.add(self.image_embedding)
            faiss.write_index(image_index, self.configs["image_emb_index_path"])
            return image_index

    def update_image_list(self, final_recs_list):
        self.image_list.extend(final_recs_list)
        self.image_list = self.image_list[-self.num_per_page:]
    
    def get_interacted_set(self, user_id, updated):
        # TODO: Load interacted set from the database
        if updated:
            with open(os.path.join(self.configs["interacted_dir"], f"interacted_{user_id}.txt"), "r", encoding="utf-8") as f:
                self.interacted_set = set([int(idx) for idx in f.read().splitlines()])
            new_interacted = self.interacted_set - set(self.image_list)
            self.image_list.extend(list(new_interacted)) 
        return self.interacted_set

    def get_recs_list(self, object_ids, num_rec_per_image):
        image_embedding = self.image_embedding[object_ids]
        D, I = self.index.search(image_embedding, num_rec_per_image)
        recs_list = []
        for i in range(len(I)):
            recs_list.append([(I[i, j], D[i, j]) for j in range(len(I[i])) if j != 0])
        return recs_list

    def __call__(self, user_id, context_info, recommended_set, default_list):
        exclude_set = self.get_interacted_set(user_id, context_info["behavior_updated"]) | recommended_set

        num_rec = self.num_per_page * 2

        if len(self.image_list) == 0:
            self.image_list = default_list
        
        len_image = len(self.image_list)
        recs_list = self.get_recs_list(self.image_list, num_rec)
        filtered_recs_list = [
            [x for x in recs if x[0] not in exclude_set] for recs in recs_list
        ]
        while any(len(recs) < self.num_per_page for recs in filtered_recs_list):
            num_rec += self.num_per_page
            recs_list = self.get_recs_list(self.image_list, num_rec)
            filtered_recs_list = [
                [x for x in recs if x[0] not in exclude_set] for recs in recs_list
            ]

        final_recs_list = [[(sim_image[0], sim_image[1], self.image_list[i]) for sim_image in filtered_recs_list[i]] for i in range(len_image)]
        sorted_final_recs_list = sorted(list(itertools.chain(*final_recs_list)), key=lambda x: x[1])
        image_names = [f"Image: {x[2]}" for x in sorted_final_recs_list]
        final_recs_list = [x[0] for x in sorted_final_recs_list]
 
        self.update_image_list(final_recs_list)
        return [final_recs_list], [image_names], len(final_recs_list)
