import os
import faiss
import random
import numpy as np


class ImageSimChannel:

    def __init__(self, index_path, embedding_path, page_rec_len, shuffle_len):
        # Embeddings of all images
        self.embeddings = np.load(embedding_path)
        self.page_rec_len = page_rec_len
        self.shuffle_len = shuffle_len

        self.index = faiss.IndexFlatIP(self.embeddings.shape[1])
        self.index.add(self.embeddings)
        faiss.write_index(self.index, index_path)

    def update_data(self, unique_log, num_image, interacted_set):
        self.image_list = unique_log.head(num_image).index.values
        self.interacted_set = interacted_set

    def get_recs_list(self, object_ids, num_rec_per_image):
        image_embeddings = self.embeddings[object_ids]
        D, I = self.index.search(image_embeddings, num_rec_per_image)
        return I[:, 1:].tolist()

    def __call__(self, recommended_set):
        exclude_set = self.interacted_set | recommended_set

        num_rec = self.page_rec_len * 2

        if len(self.image_list) == 0:
            return [], []

        recs_list = self.get_recs_list(self.image_list, num_rec)
        filtered_recs_list = [
            [x for x in recs if x not in exclude_set] for recs in recs_list
        ]
        while any(len(recs) < self.page_rec_len for recs in filtered_recs_list):
            num_rec += self.page_rec_len
            recs_list = self.get_recs_list(self.image_list, num_rec)
            filtered_recs_list = [
                [x for x in recs if x not in exclude_set] for recs in recs_list
            ]

        final_recs_list = [
            random.sample(recs[: self.shuffle_len], self.shuffle_len)
            + recs[self.shuffle_len : self.page_rec_len]
            for recs in filtered_recs_list
        ]

        image_names = [f"Image: {x}" for x in self.image_list]
        print(image_names)
        return final_recs_list, image_names
