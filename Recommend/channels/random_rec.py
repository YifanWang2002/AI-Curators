import random
from api.data import get_clicked_artworks_by_user, get_clicked_exhibitions_by_user


class RandomRecChannel:

    def __init__(self, configs, metadata):
        self.metadata = metadata
        self.configs = configs
        self.num_per_page = self.configs["num_per_page"]
        self.interacted_set = set()

    def get_interacted_set(self, user_id, updated):
        if updated:
            if self.configs["object_type"] == "artwork":
                records = get_clicked_artworks_by_user(user_id)
                id_key = "artwork_id"
            elif self.configs["object_type"] == "exhibition":
                records = get_clicked_exhibitions_by_user(user_id)
                id_key = "exhibition_id"
            else:
                records = None
                raise ValueError(f"Invalid object type: {self.configs["object_type"]}")
            if records and records["status"] == "success":
                # TODO: Analyze the ratio of interaction and decide how to update the interacted set
                self.interacted_set = self.interacted_set | set([idx[id_key] for idx in records["data"]])
        return self.interacted_set

    def __call__(self, user_id, context_info, recommended_set):
        exclude_set = self.get_interacted_set(user_id, context_info["behavior_updated"]) | recommended_set
        candidates = [cand for cand in self.metadata if cand not in exclude_set]

        seed = user_id + context_info["timestamp"]
        random.seed(seed)
        random_recs_list = random.sample(candidates, k=self.num_per_page)

        return [random_recs_list], [["Random"] * len(random_recs_list)], len(random_recs_list)
