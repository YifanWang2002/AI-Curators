import os
import ast
import json
import random
import pandas as pd
import numpy as np
from PIL import Image
from datetime import datetime
from collections import deque

from Recommend.channels.exhibition_sim import ExhibitionSimChannel
from Recommend.channels.description_sim import DescriptionSimChannel
from Recommend.channels.user_profile import UserProfileChannel
from Recommend.channels.random_rec import RandomRecChannel
from Recommend.utils.debug import save_images, read_user_log
from Recommend.api.data import get_all_exhibitions_ids, get_exhibitions_by_ids

random.seed(0)

def load_configs(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = json.load(f)
    for key, value in config_dict.items():
        if "value" in value:
            config_dict[key] = value["value"]
    return config_dict


class ExhibitionRecommender:
    def __init__(self, user_id, configs):
        self.user_id = user_id
        data = get_all_exhibitions_ids()
        if not data or data["status"] != "success":
            raise ValueError("Failed to get all artworks with error: ", data["message"])
        self.exhibition_ids = data["data"]
        self.configs = configs
        self.recommended = deque(maxlen=configs["exclude_num_recommended"])

        self.exhibition_sim_channel = ExhibitionSimChannel(configs=configs)
        self.description_sim_channel = DescriptionSimChannel(configs=configs)
        self.user_profile_channel = UserProfileChannel(user_id=user_id, configs=configs)
        self.random_rec_channel = RandomRecChannel(configs=configs, metadata=self.exhibition_ids)

        # Number of consecutive times of recommendation
        self.num_consec = 0

    def update_data(self, user_log):
        # TODO: save the history of recommendations based on current timestamp
        latest_timestamps = user_log.groupby("object_id")["timestamp"].max().to_frame()
        unique_log = latest_timestamps.sort_values("timestamp", ascending=False)
        with open(os.path.join(self.configs["interacted_dir"], f"interacted_{self.user_id}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(unique_log.head(self.configs["exclude_num_interacted"]).index.astype(str).tolist()))
        
        self.common_tags_channel.update_data(
            unique_log=unique_log,
            tag_log_len=self.configs["tag_log_len"],
            num_tag=self.configs["num_tag"],
            interacted_set=set(unique_log.head(self.configs["exclude_num_interacted"]).index)
        )

    def recommend(self, context_info):
        random_recs_list, random_names, len_random = self.random_rec_channel(
            user_id=self.user_id, context_info=context_info, recommended_set=set(self.recommended))
        exhibit_recs_list, exhibit_names, len_exhibit = self.exhibition_sim_channel(
            user_id=self.user_id, context_info=context_info, recommended_set=set(self.recommended), default_list=random_recs_list[0])
        desc_recs_list, desc_names, len_desc = self.description_sim_channel(
            user_id=self.user_id, context_info=context_info, recommended_set=set(self.recommended), default_list=random_recs_list[0])
        profile_recs_list, profile_names, len_profile = self.user_profile_channel(
            context_info=context_info, recommended_set=set(self.recommended))
        tag_recs_list, tag_names, len_tag = [], [], 0
        if not context_info["behavior_updated"]:
            self.num_consec += 1

        weights = np.array([(1 / len_exhibit) if len_exhibit > 0 else 0,
                            (1 / len_desc) if len_desc > 0 else 0,
                            (1 / len_profile) if len_profile > 0 else 0, 
                            (1 / len_random * self.num_consec) if len_random > 0 else 0])
        weights = 1 / (1 + np.exp(-weights))
        print(weights)
        all_channel_recs = (exhibit_recs_list + desc_recs_list + profile_recs_list + random_recs_list)
        all_channel_names = (exhibit_names + desc_names + profile_names + random_names)
        num_channels = 4
        positions = [0] * num_channels

        recs = []
        rec_channels = []
        while len(recs) < self.configs["num_per_page"]:
            channel_idx = random.choices(range(num_channels), weights=weights, k=1)[0]

            if positions[channel_idx] < len(all_channel_recs[channel_idx]):
                x = all_channel_recs[channel_idx][positions[channel_idx]]
                if x not in self.recommended:
                    recs.append(x)
                    rec_channels.append(all_channel_names[channel_idx][positions[channel_idx]])
                    self.recommended.append(x)
                positions[channel_idx] += 1

        print(recs)
        print(rec_channels)

        if not os.path.exists(self.configs["output_dir"]):
            os.makedirs(self.configs["output_dir"])
        rec_result = get_exhibitions_by_ids(recs)
        if rec_result["status"] == "success" and len(rec_result["data"]) > 0:
            filename = f"Page {str(context_info['page_idx']+1)}"
            rec_result_df = pd.DataFrame(rec_result["data"])
            rec_result_df.to_csv(os.path.join(self.configs["output_dir"], filename + ".csv"))
        return {
        "recommendations": recs,
        "channels": rec_channels
        }
if __name__ == "__main__":

    cur_path = os.path.dirname(os.path.abspath(__file__))
    configs = load_configs(os.path.join(cur_path, "configs_exhibition.json"))
    print(configs)

    user_id = 2
    exhibition_recommender = ExhibitionRecommender(user_id=user_id, configs=configs)

    # ==== Run the following code for each new recommendation page ===== #
    for page_idx, is_updated in enumerate([False, False, False]):
        context_info = {"timestamp": int(datetime.now().timestamp()), "behavior_updated": is_updated, "page_idx": page_idx}
        if is_updated:
            user_log = read_user_log(page_idx)

            result = metadata.iloc[user_log["object_id"].values].copy()
            if len(result) > 0:
                filename = f"user_log_{page_idx}"
                result.to_csv(os.path.join(configs["output_dir"], filename + ".csv"))
                save_images(os.path.join(configs["output_dir"], filename + ".jpg"), result["artwork_id"], result['compressed_url'])

            exhibition_recommender.update_data(user_log)

        print(f"Page {page_idx+1}")
        exhibition_recommender.recommend(context_info=context_info)