import random
import pandas as pd
from api.data import get_artworks_by_ids, get_all_artworks

class SameArtistChannel:
    def __init__(self, configs):
        self.configs = configs
        self.interacted_set = set()
        self.artist_artworks = self.load_artist_artworks()

    def fetch_api_data(self, api_func, error_msg):
        """Handle API calls and return data."""
        try:
            response = api_func()
            if response["status"] != "success":
                raise ValueError(error_msg)
            return response["data"]
        except Exception as e:
            raise RuntimeError(f"{error_msg}: {e}")

    def load_artist_artworks(self):
        data = self.fetch_api_data(get_all_artworks, "Failed to fetch tag data")
        data = pd.DataFrame(data)[["artwork_id", "artist_id"]]
        # Handle missing artist IDs by filling NaN values with a placeholder
        data["artist_id"] = data["artist_id"].fillna(-1).astype(int)  # Use -1 for unknown artists
        artist_artworks = data.groupby("artist_id")["artwork_id"].apply(list)
        return artist_artworks

    def get_artworks_for_ids(self, artwork_ids):
        """Fetch artworks for a specific tag ID."""
        return self.fetch_api_data(lambda: get_artworks_by_ids(artwork_ids), 
                                   f"Failed to fetch artworks for tag_id {artwork_ids}")
    def update_data(self, unique_log, num_artist, interacted_set):
        if unique_log.index.name == "artwork_id":
            unique_log = unique_log.reset_index()
        recent_artworks = unique_log.head(num_artist)["artwork_id"].tolist()
        artworks_data = self.get_artworks_for_ids(recent_artworks)
        self.artist_ids = [artwork['artist_id'] for artwork in artworks_data]
        self.candidates_list = []
        for artist_id in self.artist_ids:
            artwork_ids = self.artist_artworks.get(artist_id, [])
            random.shuffle(artwork_ids)
            self.candidates_list.append(artwork_ids)
        self.interacted_set = interacted_set

    def __call__(self, recommended_set):
        unique_str_integers = [str(num) for num in random.sample(range(100), 50)]
        if not recommended_set: 
            init_tags =  ['Tag: 1'] * len(unique_str_integers)
            print([unique_str_integers])
            return [unique_str_integers], [init_tags], len( unique_str_integers)
        exclude_set = self.interacted_set | recommended_set
        artist_recs_list = [
            [x for x in object_ids if x not in exclude_set]
            for object_ids in self.candidates_list
        ]
        artist_names = [f"Artist: {x}" for x in self.artist_ids]
        return artist_recs_list, artist_names, len(artist_recs_list)
