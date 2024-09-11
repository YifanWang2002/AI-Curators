import os
import ast
import random
import pandas as pd
import numpy as np
from PIL import Image
from datetime import datetime
from collections import deque

from channels.image_sim import ImageSimChannel
from channels.common_tags import CommonTagsChannel
from channels.same_artist import SameArtistChannel
from channels.random_rec import RandomRecChannel
from utils.debug import save_images

DATA_DIR = "../data"
IMAGE_DIR = "../images"
OUTPUT_DIR = "output_0911"

random.seed(0)


def get_metadata():
    metadata = pd.read_csv(os.path.join(DATA_DIR, "tags_replaced.csv"), index_col=0)
    metadata["tags"] = metadata["tags"].apply(ast.literal_eval)
    return metadata


def read_user_log():
    user_log = pd.DataFrame(
        {
            "object_id": [1258, 146, 150, 1155],
            "timestamp": [
                "2024-04-28 23:12:04.378821",
                "2024-04-28 23:12:10.378821",
                "2024-04-28 23:13:04.378821",
                "2024-04-28 23:13:10.378821",
            ],
        }
    )
    user_log["timestamp"] = pd.to_datetime(user_log["timestamp"])
    return user_log


class Recommender:
    def __init__(self, metadata, configs):
        self.metadata = metadata
        self.configs = configs
        self.recommended = deque(maxlen=configs["num_recommended"])

        self.image_sim_channel = ImageSimChannel(
            index_path=os.path.join(DATA_DIR, f"artworks_dino.index"),
            embedding_path=os.path.join(DATA_DIR, f"embeds_dino.npy"),
            page_rec_len=self.configs["page_rec_len"],
            shuffle_len=self.configs["shuffle_len"],
        )

        self.same_artist_channel = SameArtistChannel(metadata=metadata)

        self.common_tags_channel = CommonTagsChannel(
            metadata=metadata,
            tag_count_all_path=os.path.join(DATA_DIR, "tag_count_type.csv"),
        )

        self.random_rec_channel = RandomRecChannel(
            metadata=metadata, page_rec_len=self.configs["page_rec_len"]
        )

        # Number of consecutive times of recommendation
        self.num_consec = 0

    def update_data(self, user_log):
        latest_timestamps = user_log.groupby("object_id")["timestamp"].max().to_frame()
        unique_log = latest_timestamps.sort_values("timestamp", ascending=False)
        self.interacted_set = set(unique_log.head(self.configs["num_interacted"]).index)
        self.image_sim_channel.update_data(
            unique_log=unique_log,
            num_image=self.configs["num_image"],
            interacted_set=self.interacted_set,
        )
        self.same_artist_channel.update_data(
            unique_log=unique_log,
            num_artist=self.configs["num_artist"],
            interacted_set=self.interacted_set,
        )
        self.common_tags_channel.update_data(
            unique_log=unique_log,
            tag_log_len=self.configs["tag_log_len"],
            num_tag=self.configs["num_tag"],
            interacted_set=self.interacted_set,
        )
        self.random_rec_channel.update_data(
            interacted_set=self.interacted_set,
        )

        self.num_consec = 0

    def recommend(self):
        image_recs_list, image_names = self.image_sim_channel(set(self.recommended))
        artist_recs_list, artist_names = self.same_artist_channel(set(self.recommended))
        tag_recs_list, tag_names = self.common_tags_channel(set(self.recommended))
        random_recs_list, random_names = self.random_rec_channel(set(self.recommended))

        self.num_consec += 1

        weights = (
            [1 / len(image_recs_list)] * len(image_recs_list)
            + [1 / len(artist_recs_list)] * len(artist_recs_list)
            + [1 / len(tag_recs_list)] * len(tag_recs_list)
            + [
                self.num_consec
            ]  # weight for the random rec channel, which becomes larger when the user browsers recommendation pages consecutively without clicking anything
        )

        all_channel_recs = (
            image_recs_list + artist_recs_list + tag_recs_list + random_recs_list
        )
        all_channel_names = image_names + artist_names + tag_names + random_names
        num_channels = len(all_channel_recs)
        print(len(artist_recs_list))
        positions = [0] * num_channels

        recs = []
        rec_channels = []
        while len(recs) < self.configs["page_rec_len"]:
            channel_idx = random.choices(range(num_channels), weights=weights, k=1)[0]

            if positions[channel_idx] < len(all_channel_recs[channel_idx]):
                x = all_channel_recs[channel_idx][positions[channel_idx]]
                if x not in self.recommended:
                    recs.append(x)
                    rec_channels.append(all_channel_names[channel_idx])
                    self.recommended.append(x)
                    positions[channel_idx] += 1

        print(recs)
        print(rec_channels)

        result = metadata.iloc[recs].copy()
        if len(result) > 0:
            filename = f"Page {page_idx+1}"
            result.to_csv(os.path.join(OUTPUT_DIR, filename + ".csv"))
            # save_images(os.path.join(OUTPUT_DIR, filename + ".jpg"), result["image_id"], result['url'])
            save_images(os.path.join(OUTPUT_DIR, filename + ".jpg"), result["artwork_id"], result['compressed_url'])

        # for recs, artist in zip(artist_recs_list, artist_list):
        #     result = metadata.iloc[recs].copy()
        #     if len(result) > 0:
        #         filename = artist
        #         result.to_csv(os.path.join(OUTPUT_DIR, filename + ".csv"))
        #         save_images(
        #             os.path.join(OUTPUT_DIR, filename + ".jpg"), result["image_id"]
        #         )

        # for recs, tag in zip(tag_recs_list, tag_list):
        #     result = metadata.iloc[recs].copy()
        #     filename = tag
        #     result.to_csv(os.path.join(OUTPUT_DIR, filename + ".csv"))
        #     save_images(os.path.join(OUTPUT_DIR, filename + ".jpg"), result["image_id"])

        # for recs, object_id in zip(image_recs_list, image_list):
        #     result = metadata.iloc[[object_id] + list(recs)].copy()
        #     filename = str(object_id) + "_"
        #     result.to_csv(os.path.join(OUTPUT_DIR, filename + ".csv"))
        #     save_images(os.path.join(OUTPUT_DIR, filename + ".jpg"), result["image_id"])


if __name__ == "__main__":

    configs = {
        "page_rec_len": 40,  # Number of recommendations per page
        "num_interacted": 50,  # Number of unique recently interacted artworks to be excluded from recommendations
        "num_recommended": 200,  # Number of recently recommended artworks to be excluded from recommendations
        "num_image": 8,  # Number of unique artworks to create recommendations for
        # (number of sub-channels in image-based recommendation)
        "shuffle_len": 20,  # Length of recommendations to shuffle in image-based recommendation
        "num_artist": 8,  # Number of unique tags to create recommendations for
        # (number of sub-channels in tag-based recommendation)
        "num_tag": 8,  # Number of unique tags to create recommendations for
        # (number of sub-channels in tag-based recommendation)
        "tag_log_len": 20,  # Number of unique log entries for calculating tag click rates
    }

    metadata = get_metadata()
    recommender = Recommender(metadata=metadata, configs=configs)

    # ==== Run the following code for each new recommendation page ===== #

    # Whether the user has clicked a new artwork since the last time of recommendation
    for page_idx, if_new_click in enumerate([True, False, False, False, False]):
        if if_new_click:
            user_log = read_user_log()

            result = metadata.iloc[user_log["object_id"].values].copy()
            if len(result) > 0:
                filename = "user_log"
                result.to_csv(os.path.join(OUTPUT_DIR, filename + ".csv"))
                # save_images(
                #     os.path.join(OUTPUT_DIR, filename + ".jpg"), result["image_id"], result['url']
                # )
                save_images(os.path.join(OUTPUT_DIR, filename + ".jpg"), result["artwork_id"], result['compressed_url'])

            recommender.update_data(user_log)

        print(f"Page {page_idx+1}")
        recommender.recommend()
