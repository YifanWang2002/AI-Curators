import os
import faiss
import itertools
import numpy as np
import pandas as pd


class ExhibitionSimChannel:

    def __init__(self, metadata, configs):
        self.metadata = metadata
        self.artwork_exhibition_mapping = pd.read_csv(configs["artwork_exhibition_mapping_path"])
        self.configs = configs
        self.image_embedding = np.load(self.configs["image_emb_path"])
        self.exhibition_embedding = np.load(self.configs["exhibition_emb_path"])
        self.num_per_page = self.configs["num_per_page"]
        self.shuffle_len = self.configs["shuffle_len"]

        self.image_index = self.get_image_index()
        self.exhibition_index = self.get_exhibition_index()
        self.exhibition_list = []
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

    def get_exhibition_index(self):
        if os.path.exists(self.configs["exhibition_emb_index_path"]):
            return faiss.read_index(self.configs["exhibition_emb_index_path"])
        else:
            exhibition_index = faiss.IndexFlatL2(self.exhibition_embedding.shape[1])
            exhibition_index.add(self.exhibition_embedding)
            faiss.write_index(exhibition_index, self.configs["exhibition_emb_index_path"])
            return exhibition_index
        
    def get_images_from_exhibitions(self, exhibition_list):
        images = set()
        for exhibition in exhibition_list:
            images.update(self.metadata[self.metadata["exhibition_id"] == exhibition]["artwork_id"].tolist())
        return list(images)

    def update_image_list(self, final_recs_list):
        self.exhibition_list.extend(final_recs_list)
        self.exhibition_list = self.exhibition_list[-self.num_per_page:]
        self.image_list.extend(self.get_images_from_exhibitions(self.exhibition_list))
        self.image_list = self.image_list[-self.num_per_page:]
    
    def get_interacted_set(self, user_id, updated):
        # TODO: Load interacted set from the database
        if updated:
            with open(os.path.join(self.configs["interacted_dir"], f"interacted_{user_id}.txt"), "r", encoding="utf-8") as f:
                self.interacted_set = set([int(idx) for idx in f.read().splitlines()])
            new_interacted = self.interacted_set - set(self.exhibition_list)
            self.exhibition_list.extend(list(new_interacted)) 
        return self.interacted_set

    def get_recs_list_from_artwork(self, artwork_ids, num_rec_per_artwork):
        image_embedding = self.image_embedding[artwork_ids]
        D, I = self.exhibition_index.search(image_embedding, num_rec_per_artwork)
        recs_list = []
        for i in range(len(I)):
            recs_list.append([(I[i, j], D[i, j]) for j in range(len(I[i])) if j != 0])
        recs_list = [[(sim_exhibit[0], sim_exhibit[1], artwork_ids[i]) for sim_exhibit in recs_list[i]] for i in range(len(artwork_ids))]
        sorted_recs_list = sorted(list(itertools.chain(*recs_list)), key=lambda x: x[1])
        recs_names = [f"Image: {x[2]}" for x in sorted_recs_list]
        final_recs_list = [x[0] for x in sorted_recs_list]
        return final_recs_list, recs_names

    def get_recs_list_from_exhibition(self, exhibit_ids, num_rec_per_exhibit):
        exhibition_embedding = self.exhibition_embedding[exhibit_ids]
        D, I = self.exhibition_index.search(exhibition_embedding, num_rec_per_exhibit)
        recs_list = []
        for i in range(len(I)):
            recs_list.append([(I[i, j], D[i, j]) for j in range(len(I[i])) if j != 0])
        return recs_list

    def __call__(self, user_id, context_info, recommended_set, default_list):
        exclude_set = self.get_interacted_set(user_id, context_info["behavior_updated"]) | recommended_set

        if len(self.exhibition_list) == 0:
            self.exhibition_list = default_list
        
        len_exhibition = len(self.exhibition_list)
        recs_list = self.get_recs_list_from_exhibition(self.exhibition_list, self.num_per_page * 2)
        filtered_recs_list = [
            [x for x in recs if x[0] not in exclude_set] for recs in recs_list
        ]

        final_recs_list = [[(sim_exhibit[0], sim_exhibit[1], self.exhibition_list[i]) for sim_exhibit in filtered_recs_list[i]] for i in range(len_exhibition)]
        sorted_final_recs_list = sorted(list(itertools.chain(*final_recs_list)), key=lambda x: x[1])
        exhibit_names = [f"Exhibit: {x[2]}" for x in sorted_final_recs_list]
        final_recs_list = [x[0] for x in sorted_final_recs_list]

        if len(final_recs_list) < self.num_per_page:
            recs_list = self.get_recs_list_from_artwork(self.get_images_from_exhibitions(self.exhibition_list), self.num_per_page)
            exclude_set = exclude_set | set(final_recs_list)
            filtered_recs_list = [
                [x for x in recs if x[0] not in exclude_set] for recs in recs_list
            ]
            final_recs_list.extend([x[0] for x in filtered_recs_list])
            exhibit_names.extend([f"Image: {x[1]}" for x in filtered_recs_list])
 
        self.update_image_list(final_recs_list)
        return [final_recs_list], [exhibit_names], len(final_recs_list)
