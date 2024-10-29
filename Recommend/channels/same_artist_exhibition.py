import random
import pandas as pd
from api.data import get_all_exhibitions, get_art_pieces_in_exhibition, get_clicked_exhibitions_by_user

class SameArtistChannel:
    def __init__(self, configs):
        self.configs = configs
        self.interacted_set = set()
        self.exhibition_artist = self.load_exhibition_artist_mapping()

    def fetch_api_data(self, api_func, error_msg):
        """Handle API calls and return data."""
        try:
            response = api_func()
            if response["status"] != "success":
                raise ValueError(error_msg)
            return response["data"]
        except Exception as e:
            raise RuntimeError(f"{error_msg}: {e}")

    def load_exhibition_artist_mapping(self):
        exhibitions = self.fetch_api_data(get_all_exhibitions, "Failed to fetch exhibitions")
        all_artists = []
        for ex in exhibitions:
            exhibition_id = ex["exhibition_id"]
            artworks = self.get_art_pieces_for_exhibition(exhibition_id)
            for artwork in artworks:
                artist_id = artwork.get("artist_id", -1)  # Use -1 if artist_id is missing
                all_artists.append({
                    "exhibition_id": exhibition_id,
                    "artist_id": artist_id
                })

        data = pd.DataFrame(all_artists)
        data["artist_id"] = data["artist_id"].fillna(-1).astype(int)
        exhibition_artist_map = data.groupby("exhibition_id")["artist_id"].agg(lambda x: list(set(x)))
        return exhibition_artist_map

    def get_art_pieces_for_exhibition(self, exhibition_id):
        return self.fetch_api_data(lambda: get_art_pieces_in_exhibition(exhibition_id), 
                        f"Failed to fetch artworks for exhibition_id {exhibition_id}")

    def get_clicked_exhibitions_for_user(self, user_id):
        return self.fetch_api_data(lambda: get_clicked_exhibitions_by_user(user_id), 
                                   f"Failed to fetch exhibitions for user_id {user_id}")

    def update_data(self, unique_log, num_artist, interacted_set):
        """Update the artist and exhibition candidates."""
        user_exhibitions = self.get_clicked_exhibitions_for_user(4)
        user_log = pd.DataFrame(user_exhibitions)[["exhibition_id", "event_time"]]
        latest_timestamps = user_log.groupby("exhibition_id")["event_time"].max().to_frame()
        unique_log = latest_timestamps.sort_values("event_time", ascending=False)
        if unique_log.index.name == "exhibition_id":
            unique_log = unique_log.reset_index()
        recent_exhibitions = unique_log.head(num_artist)["exhibition_id"].tolist()
        all_artist_ids = []
        for exhibition in recent_exhibitions:
            artists_in_exhibition = self.exhibition_artist.get(exhibition, [])
            all_artist_ids.extend(artists_in_exhibition)
        shared_artist_counts = {}

        for exhibition_id, artist_ids in self.exhibition_artist.items():
            shared_artists = set(artist_ids) & set(all_artist_ids)  # Intersection of sets
            shared_artist_counts[exhibition_id] = len(shared_artists)

        ranked_exhibitions = sorted(
            shared_artist_counts.items(), key=lambda x: x[1], reverse=True
        )
        self.ranked_exhibition_ids = [ex_id for ex_id, _ in ranked_exhibitions]
        self.interacted_set = interacted_set

    def __call__(self, recommended_set):
        """Recommend exhibitions based on artist overlap."""
        if not recommended_set:
            # Initialize with random integers if no recommendations are available
            init_ids = [str(num) for num in random.sample(range(100), 50)]
            init_tags = ['Tag: 1'] * len(init_ids)
            return [init_ids], [init_tags], len(init_ids)

        exclude_set = self.interacted_set | recommended_set
        exhibition_recs_list = [
            ex_id for ex_id in self.ranked_exhibition_ids
            if ex_id not in exclude_set
        ]
        print("exhibition_recs_list is", exhibition_recs_list)
        return [exhibition_recs_list]
