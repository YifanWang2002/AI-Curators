import random


class RandomRecChannel:

    def __init__(self, metadata, page_rec_len):
        self.metadata = metadata
        self.page_rec_len = page_rec_len

    def update_data(self, interacted_set):
        self.interacted_set = interacted_set

    def __call__(self, recommended_set):
        exclude_set = self.interacted_set | recommended_set

        candidates = self.metadata.drop(exclude_set)
        random_recs_list = [candidates.sample(n=self.page_rec_len).index.tolist()]

        return random_recs_list, ["Random"] * len(random_recs_list)
