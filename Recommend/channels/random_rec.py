import os
from api.data import get_clicked_artworks_by_user, get_clicked_exhibitions_by_user


class RandomRecChannel:

    def __init__(self, configs, metadata):
        self.metadata = metadata
        self.configs = configs
        self.num_per_page = self.configs["num_per_page"]
        self.interacted_set = set()

    def get_interacted_set(self, user_id, updated, object_type="artwork"):
        if updated:
            if object_type == "artwork":
                records = get_clicked_artworks_by_user(user_id)
                id_key = "artwork_id"
            elif object_type == "exhibition":
                records = get_clicked_exhibitions_by_user(user_id)
                id_key = "exhibition_id"
            else:
                raise ValueError(f"Invalid object type: {object_type}")
            if records and records["status"] == "success":
                # TODO: Analyze the ratio of interaction and decide how to update the interacted set
                self.interacted_set = self.interacted_set | set([idx for idx in records["data"][id_key]])
        return self.interacted_set

    def __call__(self, user_id, context_info, recommended_set):
        exclude_set = self.get_interacted_set(user_id, context_info["behavior_updated"]) | recommended_set
        candidates = self.metadata.drop(exclude_set)

        seed = user_id + context_info["timestamp"]
        random_recs_list = candidates.sample(n=self.num_per_page, random_state=seed).index.tolist()

        return [random_recs_list], [["Random"] * len(random_recs_list)], len(random_recs_list)
