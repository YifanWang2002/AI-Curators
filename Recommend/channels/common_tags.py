import os
import random
import numpy as np
import pandas as pd


class CommonTagsChannel:
    def __init__(self, metadata, tag_count_all_path):
        self.metadata = metadata
        self.metadata_explode = metadata[["tags"]].explode("tags")
        self.tag_count_all = pd.read_csv(
            tag_count_all_path,
            usecols=["tag", "count"],
            index_col="tag",
        )
        self.tag_count_all.rename(columns={"count": "count_all"}, inplace=True)
        self.tag_artworks = self.metadata_explode.groupby("tags").apply(
            lambda x: list(x.index)
        )

    def update_data(self, unique_log, tag_log_len, num_tag, interacted_set):
        id_tag_time = (
            unique_log.head(tag_log_len)
            .join(self.metadata)[["tags", "timestamp"]]
            .explode(column="tags")
        )
        tag_time_count = (
            id_tag_time.groupby("tags")
            .agg(timestamp=("timestamp", "max"), count=("timestamp", "size"))
            .join(self.tag_count_all)
        )
        tag_time_count["click_rate"] = (
            tag_time_count["count"] / tag_time_count["count_all"]
        )
        tag_time_count.drop(columns=["count", "count_all"], inplace=True)
        tag_sorted = tag_time_count.sort_values(
            by=["click_rate", "timestamp"], ascending=[False, False]
        ).head(num_tag)
        self.tag_list = tag_sorted.index.tolist()
        tag_rate_dict = tag_sorted["click_rate"].to_dict()

        self.candidates_list = []
        for tag in self.tag_list:
            object_ids = self.tag_artworks.loc[tag]
            obj_tag_scores = (
                self.metadata.loc[object_ids]["tags"]
                .apply(
                    lambda tags: sum(
                        tag_rate_dict[tag] for tag in tags if tag in tag_rate_dict
                    )
                )
                .sort_values(ascending=False)
            )
            self.candidates_list.append(obj_tag_scores.index.tolist())

        # Get Related Tags, i.e., tags co-occuring with the selected tags

        # unique_object_ids = self.metadata_explode[
        #     self.metadata_explode["tags"].isin(self.tag_list)
        # ].index.unique()

        # related_tags_count = (
        #     self.metadata_explode.loc[unique_object_ids]["tags"]
        #     .value_counts()
        #     .drop(self.tag_list)
        #     .to_frame()
        # ).join(self.tag_count_all)
        # related_tags_count["occur_rate"] = (
        #     related_tags_count["count"] / related_tags_count["count_all"]
        # )
        # self.related_tags = related_tags_count.sort_values(
        #     "occur_rate", ascending=False
        # ).index.tolist()
        # print(self.related_tags)

        self.interacted_set = interacted_set

        # self.num_tag = num_tag

    def __call__(self, recommended_set):
        exclude_set = self.interacted_set | recommended_set

        # if self.num_consec <= self.num_tag and self.num_consec < len(self.related_tags):
        #     new_tag = self.related_tags[self.num_consec - 1]
        #     self.tag_list.append(new_tag)
        #     object_ids = self.tag_artworks.loc[new_tag]
        #     random.shuffle(object_ids)
        #     self.candidates_list.append(object_ids)

        tag_recs_list = [
            [x for x in object_ids if x not in exclude_set]
            for object_ids in self.candidates_list
        ]

        tag_names = [f"Tag: {x}" for x in self.tag_list]
        # print(tag_names)
        return tag_recs_list, tag_names
