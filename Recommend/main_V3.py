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
from channels.cold_start import ColdStartChannel
from utils.debug import save_images
from exhibition_curator import ExhibitionCurator

from transformers import AutoTokenizer, AutoModel, AutoModelForMaskedLM
import torch
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import euclidean
from time import time
import datetime
import json

import warnings
warnings.filterwarnings("ignore")

DATA_DIR = "Recommend/data"
IMAGE_DIR = "GPT/images"
OUTPUT_DIR = "Recommend/output"

random.seed(0)


def get_metadata():
    metadata = pd.read_csv(os.path.join(DATA_DIR, "tags_replaced.csv"), index_col=0, encoding='utf-8')
    metadata["tags"] = metadata["tags"].apply(ast.literal_eval)
    return metadata


def read_user_log(user_id):
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
    user_log_new = {
        "artists": [
            "Claude Monet", "Nicolaes Maes", "Franco-Flemish 15th Century", 
            "Rembrandt", "Pablo Picasso", "Vincent van Gogh", "Leonardo da Vinci", 
            "Georgia O'Keeffe", "Jackson Pollock", "Frida Kahlo", "Salvador Dali", 
            "Andy Warhol", "Henri Matisse", "Edvard Munch", "Gustav Klimt"
        ],
        "styles": [
            "Impressionism", "Realism", "Chiaroscuro", "Early Renaissance", 
            "Cubism", "Post-Impressionism", "Surrealism", "Modernism", 
            "Abstract Expressionism", "Pop Art", "Expressionism", "Symbolism", 
            "Art Nouveau", "Baroque", "Fauvism"
        ],
        "themes": [
            "Nature", "landscapes", "Tranquility", "Everyday Life", "Aging", 
            "Religious Themes", "Abstract", "Still Life", "Portraits", "Fantasy", 
            "Urban Life", "Mythology", "Dreams", "Identity", "Conflict", 
            "Love", "Death", "Political Commentary"
        ],
        "movements": [
            "Impressionism", "Dutch Golden Age", "Northern Renaissance", 
            "Early Netherlandish", "Modern Art", "Post-Impressionism", "Renaissance", 
            "American Modernism", "Abstract Expressionism", "Pop Art", "Surrealism", 
            "Expressionism", "Symbolism", "Art Nouveau", "Baroque"
        ]
    }
    all_users = {
        'User001': user_log_new,
        'User002': user_log
    }
    current_user = all_users[user_id]
    if 'timestamp' not in current_user:
        is_new = True
    else:
        is_new = False
    
    return is_new, current_user


class Recommender:
    def __init__(self, metadata, configs, embedding_model = SentenceTransformer('all-MiniLM-L6-v2')):
        self.metadata = metadata
        self.configs = configs
        self.user_logs = {}
        self.recommended = deque(maxlen=configs["num_recommended"])

        self.image_sim_channel = ImageSimChannel(
            index_path=os.path.join(DATA_DIR, f"artworks_dino.index"),
            embedding_path=os.path.join(DATA_DIR, f"search_embeds_dino.npy"),
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

        self.cold_start_channel = ColdStartChannel(
            metadata=metadata,
            embedding_model=embedding_model,
            top_k=self.configs["cold_start_top_k"]
        )

        # Number of consecutive times of recommendation
        self.num_consec = 0
        self.is_new = False

    def update_data(self, user_log, is_new = False):
        # self.user_logs[user_id] = user_log
        self.is_new = is_new
        if self.is_new:
            self.cold_start_channel.update_data(user_log)
        else:
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

    def recommend(self, user_id):
        current_time = datetime.datetime.now()
        recommendation_output = f"{OUTPUT_DIR}/{user_id}/{current_time}"
        recommendation_output = recommendation_output.replace(" ", "_")
        recommendation_output = recommendation_output.replace(":", "-")
        user_directory = f"{OUTPUT_DIR}/{user_id}"
        if not os.path.exists(user_directory):
            os.makedirs(user_directory)
        if not os.path.exists(recommendation_output):
            os.makedirs(recommendation_output)
        if self.is_new:
            # print('         Cold start channel...')
            cold_start_list = self.cold_start_channel()
            result = metadata.iloc[cold_start_list].copy()
            result["channel"] = 'cold_start'
            result["channel_weight"] = 1
            result = result[['image_id', 'channel', 'channel_weight']]
            if len(result) > 0:
                filename = f"Top {len(result)} Recommendations"
                result.to_csv(os.path.join(recommendation_output, filename + ".csv"), index=False, encoding='utf-8')
                # save_images(os.path.join(recommendation_output, filename + ".jpg"), result["image_id"])
        else:
            # print('         Normal recommendation...')
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
            # normalize weights so that it sum to 1
            total_weight = sum(weights)
            weights = [weight / total_weight for weight in weights]

            all_channel_recs = (
                image_recs_list + artist_recs_list + tag_recs_list + random_recs_list
            )
            # all_channel_names = image_names + artist_names + tag_names + random_names
            # get the channel names for each list in all_channel_recs
            channels = ["image"] * len(image_recs_list) + ["artist"] * len(artist_recs_list) + ["tag"] * len(tag_recs_list) + ["random"] * len(random_recs_list)
            num_channels = len(all_channel_recs)
            # print(len(artist_recs_list))
            positions = [0] * num_channels

            recs = []
            rec_channels = []
            channel_weights = []
            while len(recs) < self.configs["page_rec_len"]:
                channel_idx = random.choices(range(num_channels), weights=weights, k=1)[0]

                if positions[channel_idx] < len(all_channel_recs[channel_idx]):
                    x = all_channel_recs[channel_idx][positions[channel_idx]]
                    if x not in self.recommended:
                        recs.append(x)
                        rec_channels.append(channels[channel_idx])
                        channel_weights.append(weights[channel_idx])
                        self.recommended.append(x)
                        positions[channel_idx] += 1

            # print(recs)
            # print(rec_channels)

            result = metadata.iloc[recs].copy()
            result["channel"] = rec_channels
            result["channel_weight"] = channel_weights
            if len(result) > 0:
                result = result[['image_id', 'channel', 'channel_weight']]
                filename = f"Top {len(result)} Recommendations"
                result.to_csv(os.path.join(recommendation_output, filename + ".csv"), index=True, encoding='utf-8')
                # save_images(os.path.join(recommendation_output, filename + ".jpg"), result["image_id"])
        if self.configs["as_exhibition"]:
            self.curator = ExhibitionCurator(api_key="your key", metadata=metadata)
            exhibitions = self.curator.curate(result)
            for i, exhibition in enumerate(exhibitions):
                with open(os.path.join(recommendation_output, f'Exhibition_{i}' + ".json"), 'w') as f:
                    json.dump(exhibition, f, indent=4)
                f.close()
                save_images(os.path.join(recommendation_output, f'Exhibition_{i}' + ".jpg"), exhibition['art_pieces'])
            # check if the exhibition 
            
        return recommendation_output
if __name__ == "__main__":
    start = time()
    # os.chdir('/Users/marktang/Metaverse_Museum/AI-Curators/Recommend')
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f'Output directory created as: {OUTPUT_DIR}')
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
        "cold_start_top_k": 55, # Number of top tags to be used in the cold start channel
        "as_exhibition": True,  # Whether the recommendations are for an exhibition
    }
    print('Preparing system...')
    print(os.getcwd())
    metadata = get_metadata()
    recommender = Recommender(metadata=metadata, configs=configs)
    system_ready_time = time()
    print(f'System ready. Time taken: {system_ready_time-start}')
    # ==== Run the following code for each new recommendation page ===== #

    # # Whether the user has clicked a new artwork since the last time of recommendation
    # for page_idx, if_new_click in enumerate([True, False]):
    print('Starting recommendation...')
    for user_id in ['User001', 'User002']:
        print(f'    Recommending for {user_id}...')
        checkpoint_time = time()
        is_new, user_log = read_user_log(user_id)
        print(f'        {user_id} is new: {is_new}')
        recommender.update_data(user_log, is_new=is_new)
        current_OUTPUT_DIR = recommender.recommend(user_id)
        if not is_new:
            result = metadata.iloc[user_log["object_id"].values].copy()
            if len(result) > 0:
                filename = "user_log"
                result.to_csv(os.path.join(current_OUTPUT_DIR, filename + ".csv"))
                save_images(
                    os.path.join(current_OUTPUT_DIR, filename + ".jpg"), result["image_id"]
                )
        print(f'        Recommendation takes {time()-checkpoint_time} seconds.')
        print(f'    Recommendation for {user_id} completed.')
    print(f'Recommendation completed. Recommendation time: {time()-system_ready_time}')
    end = time()
    print(f'Time taken: {end-start}')
