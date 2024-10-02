import os
import ast
import json
import random
import pandas as pd
import numpy as np
from PIL import Image
from datetime import datetime
from collections import deque

from channels.exhibition_sim import ExhibitionSimChannel
from channels.description_sim import DescriptionSimChannel
from channels.common_tags_wenqing import CommonTagsChannel
from channels.common_tags import CommonTagsChannel as CommonTagsChannelBackup
from channels.user_profile import UserProfileChannel
from channels.random_rec import RandomRecChannel
from utils.debug import save_images, read_user_log

random.seed(0)


def get_metadata(data_dir):
    metadata = pd.read_csv(os.path.join(data_dir, "tags_replaced.csv"), index_col=0)
    metadata["tags"] = metadata["tags"].apply(ast.literal_eval)
    return metadata


def load_configs(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = json.load(f)
    for key, value in config_dict.items():
        if "value" in value:
            config_dict[key] = value["value"]
    return config_dict


class ExhibitionRecommender:
    def __init__(self, user_id, metadata, configs):
        self.user_id = user_id
        self.metadata = metadata
        self.configs = configs
        self.recommended = deque(maxlen=configs["exclude_num_recommended"])

        self.exhibition_sim_channel = ExhibitionSimChannel(metadata=metadata, configs=configs)
        self.description_sim_channel = DescriptionSimChannel(metadata=metadata, configs=configs)
        self.user_profile_channel = UserProfileChannel(metadata=metadata, user_id=user_id, configs=configs)
        self.common_tags_channel = CommonTagsChannel(metadata=metadata, configs=configs)
        self.common_tags_channel_backup = CommonTagsChannelBackup(metadata=metadata, tag_count_all_path=configs["tag_count_type_path"])
        self.random_rec_channel = RandomRecChannel(configs=configs, metadata=metadata)

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
        tag_recs_list, tag_names, len_tag = self.common_tags_channel(set(self.recommended))
        # hotfix:
        backup = False
        if len_tag == 0:
            tag_recs_list, tag_names, len_tag = self.common_tags_channel_backup(set(self.recommended))
            backup = True
        if not context_info["behavior_updated"]:
            self.num_consec += 1

        weights = np.array([1 / len_exhibit, 1 / len_desc, 1 / len_profile, 1 / len_tag, 1 / len_random * self.num_consec])
        weights = 1 / (1 + np.exp(-weights))
        print(weights)
        all_channel_recs = (exhibit_recs_list + desc_recs_list + profile_recs_list + tag_recs_list + random_recs_list)
        all_channel_names = (exhibit_names + desc_names + profile_names + tag_names + random_names)
        num_channels = 5
        positions = [0] * num_channels

        recs = []
        rec_channels = []
        while len(recs) < self.configs["num_per_page"]:
            channel_idx = random.choices(range(num_channels), weights=weights, k=1)[0]

            if positions[channel_idx] < len(all_channel_recs[channel_idx]):
                x = all_channel_recs[channel_idx][positions[channel_idx]]
                # TODO: Add logic to remove artworks that have been recommended before to allow duplicates
                if x not in self.recommended:
                    recs.append(x)
                    rec_channels.append(all_channel_names[channel_idx][positions[channel_idx]])
                    self.recommended.append(x)
                    positions[channel_idx] += 1

        print(recs)
        print(rec_channels)

        rec_result = self.metadata.iloc[recs].copy()
        if len(rec_result) > 0:
            filename = f"Page {str(context_info['page_idx']+1)}"
            rec_result.to_csv(os.path.join(self.configs["output_dir"], filename + ".csv"))
            try:
                save_images(os.path.join(self.configs["output_dir"], filename + ".jpg"), rec_result["artwork_id"], rec_result['compressed_url'])
            except Exception as e:
                print(e)

if __name__ == "__main__":

    cur_path = os.path.dirname(os.path.abspath(__file__))
    configs = load_configs(os.path.join(cur_path, "configs.json"))
    print(configs)

    metadata = get_metadata(configs["data_dir"])
    user_id = 3
    exhibition_recommender = ExhibitionRecommender(user_id=user_id, metadata=metadata, configs=configs)

    # ==== Run the following code for each new recommendation page ===== #
    for page_idx, is_updated in enumerate([False, True, False]):
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