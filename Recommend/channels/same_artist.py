import random
import pandas as pd
from api.data import get_artworks_by_artist_id, get_artworks_by_same_artist, get_clicked_artworks_by_user

class SameArtistChannel:
    def __init__(self, configs):
        self.configs = configs
        self.interacted_set = set()
    
    def get_interacted_set(self, user_id, updated):
        if updated:
            records = get_clicked_artworks_by_user(user_id)
            if records and records["status"] == "success":
                # TODO: Analyze the ratio of interaction and decide how to update the interacted set
                self.interacted_set = self.interacted_set | set([idx["artwork_id"] for idx in records["data"]])
        return self.interacted_set

    def __call__(self, recommended_set):
        artist_names = []
        recs_list = []
        if not recommended_set or len(recommended_set) == 0:
            recommended_set = random.sample(range(self.configs["default_artist_num"]), self.configs["num_per_page"])
        candidate_list = self.interacted_set | set(recommended_set)
        for candidate in candidate_list:
            if isinstance(candidate, int):
                data = get_artworks_by_artist_id(candidate)
            else:
                data = get_artworks_by_same_artist(candidate)
            if data and data["status"] == "success":
                recs_list.extend([x for x in data["data"]])
                artist_names.extend([f"Artist: {candidate}"] * len(data["data"]))
        return [recs_list], [artist_names], len(recs_list)
