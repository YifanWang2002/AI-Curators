import random


class SameArtistChannel:

    def __init__(self, metadata):
        self.metadata = metadata
        self.artist_artworks = metadata.groupby("artist_display").apply(
            lambda x: list(x.index)
        )

    def update_data(self, unique_log, num_artist, interacted_set):
        self.artist_list = (
            unique_log.head(num_artist).join(self.metadata)["artist_display"].values
        )

        self.candidates_list = []
        for artist in self.artist_list:
            object_ids = self.artist_artworks.loc[artist]
            random.shuffle(object_ids)
            self.candidates_list.append(object_ids)

        self.interacted_set = interacted_set

    def __call__(self, recommended_set):
        exclude_set = self.interacted_set | recommended_set
        artist_recs_list = [
            [x for x in object_ids if x not in exclude_set]
            for object_ids in self.candidates_list
        ]

        artist_names = [f"Artist: {x}" for x in self.artist_list]
        print(artist_names)
        return artist_recs_list, artist_names
