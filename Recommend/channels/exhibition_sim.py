import os
import faiss
import random
import itertools
import numpy as np
import pandas as pd
from Recommend.api.data import get_clicked_exhibitions_by_user, get_artworks_id_mapping, get_art_pieces_in_exhibition


class ExhibitionSimChannel:

    def __init__(self, configs):
        self.configs = configs
        self.image_embedding = np.load(self.configs["image_emb_path"])
        self.artwork_to_embedding, self.embedding_to_artwork = self.get_artwork_id_mapping()
        self.exhibition_embedding = np.load(self.configs["exhibition_emb_path"])
        self.num_per_page = self.configs["num_per_page"]

        self.image_index = self.get_image_index()
        self.exhibition_index = self.get_exhibition_index()
        self.exhibition_list = []
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
            art_pieces = get_art_pieces_in_exhibition(exhibition)
            if art_pieces and art_pieces["status"] == "success":
                images.update([art_piece["artwork_id"] for art_piece in art_pieces["data"]])
        return list(images)

    def update_image_list(self, final_recs_list):
        self.exhibition_list.extend(final_recs_list)
        self.exhibition_list = self.exhibition_list[-self.num_per_page:]
    
    def get_interacted_set(self, user_id, updated):
        if updated:
            records = get_clicked_exhibitions_by_user(user_id)
            if records and records["status"] == "success":
                # TODO: Analyze the ratio of interaction and decide how to update the interacted set
                self.interacted_set = set([idx["exhibition_id"] for idx in records["data"]])
            new_interacted = self.interacted_set - set(self.exhibition_list)
            self.exhibition_list.extend(list(new_interacted)) 
        return self.interacted_set

    def get_recs_list_from_artwork(self, artwork_ids, num_rec_per_artwork):
        artwork_ids = random.sample(artwork_ids, min(len(artwork_ids), num_rec_per_artwork))
        image_embedding = self.image_embedding[[self.artwork_to_embedding[artwork_id] for artwork_id in artwork_ids]]
        D, I = self.exhibition_index.search(image_embedding, num_rec_per_artwork)
        recs_list = []
        for i in range(len(I)):
            recs_list.append([(I[i, j], D[i, j]) for j in range(len(I[i])) if j != 0])
        recs_list = [[(sim_exhibit[0], sim_exhibit[1], artwork_ids[i]) for sim_exhibit in recs_list[i]] for i in range(len(artwork_ids))]
        sorted_recs_list = sorted(list(itertools.chain(*recs_list)), key=lambda x: x[1])
        recs_names = [f"Image: {x[2]}" for x in sorted_recs_list]
        final_recs_list = [int(x[0]) for x in sorted_recs_list]
        return final_recs_list, recs_names

    def get_recs_list_from_exhibition(self, exhibit_ids, num_rec_per_exhibit):
        exhibition_embedding = self.exhibition_embedding[exhibit_ids]
        D, I = self.exhibition_index.search(exhibition_embedding, num_rec_per_exhibit)
        recs_list = []
        for i in range(len(I)):
            recs_list.append([(int(I[i, j]), D[i, j]) for j in range(len(I[i])) if j != 0])
        return recs_list

    def __call__(self, user_id, context_info, recommended_set, default_list):
        exclude_set = self.get_interacted_set(user_id, context_info["behavior_updated"]) | recommended_set

        if len(self.exhibition_list) == 0:
            self.exhibition_list = default_list.copy()
        
        len_exhibition = len(self.exhibition_list)
        recs_list = self.get_recs_list_from_exhibition(self.exhibition_list, self.num_per_page * 2)
        filtered_recs_list = [
            [x for x in recs if x[0] not in exclude_set] for recs in recs_list
        ]

        final_recs_list = [[(sim_exhibit[0], sim_exhibit[1], self.exhibition_list[i]) for sim_exhibit in filtered_recs_list[i]] for i in range(len_exhibition)]
        sorted_final_recs_list = sorted(list(itertools.chain(*final_recs_list)), key=lambda x: x[1])
        exhibit_names = [f"Exhibition: {x[2]}" for x in sorted_final_recs_list]
        final_recs_list = [x[0] for x in sorted_final_recs_list]

        if len(final_recs_list) < self.num_per_page:
            recs_list_by_images, recs_names_by_images = self.get_recs_list_from_artwork(self.get_images_from_exhibitions(self.exhibition_list), self.num_per_page)
            exclude_set = exclude_set | set(final_recs_list)
            for i, recs in enumerate(recs_list_by_images):
                if recs in exclude_set:
                    recs_list_by_images.pop(i)
                    recs_names_by_images.pop(i)
            final_recs_list.extend(recs_list_by_images)
            exhibit_names.extend(recs_names_by_images)
        self.update_image_list(final_recs_list)
        return [final_recs_list], [exhibit_names], len(final_recs_list)
