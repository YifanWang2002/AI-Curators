import os
import faiss
import itertools
import numpy as np
from Recommend.api.data import get_clicked_artworks_by_user, get_artworks_id_mapping


class ImageSimChannel:

    def __init__(self, configs):
        # Embeddings of all images
        self.configs = configs
        self.image_embedding = np.load(self.configs["image_emb_path"])
        self.artwork_to_embedding, self.embedding_to_artwork = self.get_artwork_id_mapping()
        self.num_per_page = self.configs["num_per_page"]
        self.shuffle_len = self.configs["shuffle_len"]

        self.index = self.get_image_index()
        self.image_list = []
        self.interacted_set = set()

    def get_artwork_id_mapping(self):
        records = get_artworks_id_mapping()
        if records and records["status"] == "success":
            artwork_to_embedding = records["data"]
            embedding_to_artwork = {int(v): k for k, v in artwork_to_embedding.items()}
            return artwork_to_embedding, embedding_to_artwork
        return {}, {}
    
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
        if updated:
            records = get_clicked_artworks_by_user(user_id)
            if records and records["status"] == "success":
                # TODO: Analyze the ratio of interaction and decide how to update the interacted set
                self.interacted_set = set([idx["artwork_id"] for idx in records["data"]])
            new_interacted = self.interacted_set - set(self.image_list)
            self.image_list.extend(list(new_interacted)) 
        return self.interacted_set

    def get_recs_list(self, image_ids, num_rec_per_image):
        image_embedding = self.image_embedding[[self.artwork_to_embedding[image_id] for image_id in image_ids]]
        D, I = self.index.search(image_embedding, num_rec_per_image)
        recs_list = []
        for i in range(len(I)):
            recs_list.append([(self.embedding_to_artwork[I[i, j]], D[i, j]) for j in range(len(I[i])) if j != 0])
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
