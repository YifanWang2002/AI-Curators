import os
import random
import numpy as np
import pandas as pd
from collections import defaultdict


class CommonTagsChannel:
    def __init__(self, metadata, configs):
        self.metadata = metadata
        self.configs = configs
        self.metadata_explode = metadata[["tags"]].explode("tags")
        self.tag_count_all = pd.read_csv(
            self.configs["tag_count_type_path"],
            usecols=["tag", "count", "type"],
            index_col="tag",
        )
        self.tag_count_all.rename(columns={"count": "tag_count_all"}, inplace=True)
        type_count_all = self.tag_count_all.groupby("type")["tag_count_all"].sum()
        self.tag_count_all["type_count_all"] = self.tag_count_all["type"].map(type_count_all)
        self.tag_artworks = self.metadata_explode.groupby("tags").apply(
            lambda x: list(x.index)
        )
        self.interacted_set = set()
        self.tag_list = ["Nature", "Realism"]
        self.all_list = defaultdict(list)
        self.init_tag_candidates()

    def init_tag_candidates(self):
        self.candidates_list = []
        tag_rate_dict = {"Nature": 0.9, "Realism": 0.5}
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

    def update_data(self, unique_log, tag_log_len, num_tag, interacted_set):
        id_tag_time = (
            unique_log.head(tag_log_len)
            .join(self.metadata)[["tags", "timestamp"]]
            .explode(column="tags")
        )
        # print("#####id_tag_time###")
        # print(id_tag_time)
        tag_time_count = (
            id_tag_time.groupby("tags")
            .agg(timestamp=("timestamp", "max"), tag_count=("timestamp", "size"))
            .join(self.tag_count_all)
        )
        # print("#####tag_time_count###")
        # print(tag_time_count)

        # Count occurrences of each type
        type_time_count = (
            id_tag_time.join(self.tag_count_all[['type']], on='tags')
            .groupby('type')
            .agg(
                timestamp=("timestamp", "max"),
                type_count=('tags', 'size')
            )
        ).join(self.tag_count_all.groupby('type').agg(type_count_all=('tag_count_all', 'sum')), on='type')

        tag_time_count["tag_click_rate"] = (
            tag_time_count["tag_count"] / tag_time_count["tag_count_all"]
        )
        type_time_count["type_click_rate"] = (
             type_time_count["type_count"] / type_time_count["type_count_all"]
        )

        tag_time_count.drop(columns=["tag_count", "tag_count_all"], inplace=True)
        type_time_count.drop(columns=["type_count", "type_count_all"], inplace=True)

        tag_sorted = tag_time_count.sort_values(
            by=["tag_click_rate", "timestamp"], ascending=[False, False]
        )

        type_sorted = type_time_count.sort_values(
            by=["type_click_rate", "timestamp"], ascending=[False, False]
        )

        self.tag_list = tag_sorted.index.tolist()
        self.tag_rate_dict = tag_sorted["tag_click_rate"].to_dict()
        print(self.tag_rate_dict)

        self.type_list = type_sorted.index.tolist()
        self.type_rate_dict = type_sorted["type_click_rate"].to_dict()
        # Create dictionaries for each type
        results = {}
        for tag_type in self.type_list:
            # Filter tags by type
            tags_of_type = tag_sorted[tag_sorted.index.isin(self.tag_count_all[self.tag_count_all['type'] == tag_type].index)]
            top_tags = tags_of_type.head(num_tag) 
            results[tag_type] = top_tags["tag_click_rate"].to_dict()
        print(results)

        self.all_list = defaultdict(list)
        for tag_type in self.type_list:
            self.candidates_list = []
            self.tag_list = list(results[tag_type].keys())
            self.loop_tag_rate_dict = results[tag_type]
            self.candidates_tags = []
            for tag in self.tag_list:
                object_ids = self.tag_artworks.loc[tag]
                obj_tag_scores = (
                    self.metadata.loc[object_ids]["tags"]
                    .apply(
                        lambda tags: sum(
                            self.loop_tag_rate_dict[tag] for tag in tags if tag in self.loop_tag_rate_dict
                        )
                    )
                    .sort_values(ascending=False)
                )
                self.candidates_list.append(obj_tag_scores.index.tolist())
            tag_names = [f"Tag: {x}" for x in self.tag_list]
            self.all_list[tag_type] = [self.candidates_list, tag_names]

        if interacted_set:
            self.interacted_set = interacted_set
        else:
            self.interacted_set = set()

    def calculate_weight(self, tag_weight, type_weight, alpha=0.7):
        blended_score = alpha * tag_weight + (1 - alpha) * type_weight
        return blended_score

    def __call__(self, recommended_set):
        exclude_set = self.interacted_set | recommended_set

        # Create a filtered version of all_list
        filtered_all_list = {}

        for tag_type, object_ids in self.all_list.items():
            filtered_object_ids = [
                [x for x in ids if x not in exclude_set] for ids in object_ids[0]
            ]
            filtered_object_ids = [ids for ids in filtered_object_ids if ids]

            filtered_tags = [
                tag for i, tag in enumerate(object_ids[1]) if any(p not in exclude_set for p in object_ids[0][i])
            ]
            # Store the filtered results
            filtered_all_list[tag_type] = [filtered_object_ids, filtered_tags]
       
        artwork_weights = []
        guaranteed_artworks = []
        total_artworks = self.configs["num_per_page"]

        # Step 1: Ensure at least one artwork from each type by selecting the highest-ranked artwork for each type
        for type_key, (artwork_groups, tags) in filtered_all_list.items():
            type_weight = self.type_rate_dict[type_key]
            
            # Prepare a list to hold all artworks in this type along with their weights
            type_artworks_with_scores = []

            # For each group of artworks and their corresponding tag
            for idx, artwork_group in enumerate(artwork_groups):
                tag = tags[idx]  # Get the corresponding tag for this group
                # print("self.tag_rate_dict is", self.tag_rate_dict)
                tag_weight = self.tag_rate_dict[tag.split(": ")[1]]  # Get the tag's weight

                # Calculate the blended score for each artwork in this group
                for artwork in artwork_group:
                    blended_weight = self.calculate_weight(tag_weight, type_weight, 0.7)
                    type_artworks_with_scores.append((artwork, tag, type_key, blended_weight))
            
            # Select the highest-scored artwork for this type
            highest_scored_artwork = max(type_artworks_with_scores, key=lambda x: x[3])
            guaranteed_artworks.append(highest_scored_artwork)

            # Add all other artworks to the main pool for ranking later
            artwork_weights.extend(type_artworks_with_scores)

        # Step 2: Remove guaranteed artworks from the pool to avoid duplication
        remaining_artwork_weights = [
            aw for aw in artwork_weights if aw[0] not in [g[0] for g in guaranteed_artworks]
        ]

        # Step 3: Sort the remaining artworks by their blended weight in descending order
        remaining_artwork_weights.sort(key=lambda x: x[3], reverse=True)

        # Step 4: Select the remaining top artworks to complete the total number
        num_remaining_artworks = total_artworks - len(guaranteed_artworks)
        selected_remaining_artworks = remaining_artwork_weights[:num_remaining_artworks]

        # Combine the guaranteed artworks with the remaining selected artworks
        final_artwork_selection = guaranteed_artworks + selected_remaining_artworks

        # Sort the final selection by blended score
        final_artwork_selection.sort(key=lambda x: x[3], reverse=True)

        # Split into three lists: one for selected artworks, one for corresponding tags, and one for corresponding types
        selected_artworks = [artwork for artwork, tag, type_key, weight in final_artwork_selection]
        selected_tags = [tag for artwork, tag, type_key, weight in final_artwork_selection]
        selected_types = [type_key for artwork, tag, type_key, weight in final_artwork_selection]
        # print(selected_artworks)
        # print(selected_tags)
        # print(selected_types)

        return [selected_artworks], [selected_tags], len(selected_artworks)
