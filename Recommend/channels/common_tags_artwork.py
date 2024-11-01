import numpy as np
import pandas as pd
from collections import defaultdict
from Recommend.api.data import get_clicked_artworks_by_user, get_all_tags, get_artworks_by_tag_id, get_tags_by_artwork_ids, get_clicked_artworks_by_user, get_tags_click_rates, get_type_click_rates

class CommonTagsChannel:
    def __init__(self, configs):
        self.configs = configs
        self.tag_count_all = self.load_tag_count()
        self.interacted_set = set()
        self.tag_list = [1, 2]
        self.all_list = defaultdict(list)
        self.init_tag_candidates()

    def load_tag_count(self):
        """Load tag counts using the API."""
        data = self.fetch_api_data(get_all_tags, "Failed to fetch tag data")
        tag_df = pd.DataFrame(data).rename(columns={
            "tag_type": "type", "count": "tag_count_all"
        })[["tag_id", "tag_name", "tag_count_all", "type"]]
        tag_df.set_index("tag_id", inplace=True)
        tag_df["type_count_all"] = tag_df["type"].map(tag_df.groupby("type")["tag_count_all"].sum())
        return tag_df

    def fetch_api_data(self, api_func, error_msg):
        """Handle API calls and return data."""
        try:
            response = api_func()
            if response["status"] != "success":
                raise ValueError(error_msg)
            return response["data"]
        except Exception as e:
            raise RuntimeError(f"{error_msg}: {e}")

    def get_clicked_artworks_for_user(self, user_id):
        return self.fetch_api_data(lambda: get_clicked_artworks_by_user(user_id), 
                                   f"Failed to fetch artworks for tag_id {user_id}")


    def get_artworks_for_tag_id(self, tag_id):
        """Fetch artworks for a specific tag ID."""
        return self.fetch_api_data(lambda: get_artworks_by_tag_id(tag_id), 
                                   f"Failed to fetch artworks for tag_id {tag_id}")

    def get_tags_for_artwork_ids(self, artwork_ids):
        """Fetch tags for artworks."""
        return self.fetch_api_data(lambda: get_tags_by_artwork_ids(artwork_ids), 
                                   f"Failed to fetch tags for artwork IDs {artwork_ids}")

    def get_tags_for_click_rates(self, tag_ids):
        """Fetch tags for artworks."""
        return self.fetch_api_data(lambda: get_tags_click_rates(tag_ids), 
                                   f"Failed to fetch tags for artwork IDs {tag_ids}")
    def get_types_for_click_rates(self, tag_ids):
        """Fetch tags for artworks."""
        return self.fetch_api_data(lambda: get_type_click_rates(tag_ids), 
                                   f"Failed to fetch tags for artwork IDs {tag_ids}")

    def init_tag_candidates(self):
        self.candidates_list = []
        tag_rate_dict = {1: 0.9, 2: 0.5} # 1 for "Nature" 2 for "Realism"
        for tag in self.tag_list:
            # Use the tag ID from your loaded tag data (self.tag_count_all)
            if tag not in self.tag_count_all.index:
                print(f"Warning: Tag '{tag}' not found in tag data.")
                continue
            artwork_ids = self.get_artworks_for_tag_id(tag)  # Fetch artworks using API

            if not artwork_ids:
                print(f"No artworks found for tag: {tag}")
                continue
            art_tags_data = self.get_tags_for_artwork_ids(artwork_ids)
            art_tag_scores = pd.Series(art_tags_data).apply(
                lambda tags: sum(tag_rate_dict.get(tag, 0) for tag in tags)
            ).sort_values(ascending=False)
            self.candidates_list.append(art_tag_scores.index.tolist())
        self.init_list = self.candidates_list[0][0:50]

    def update_data(self, unique_log, tag_log_len, num_tag, interacted_set):
        if unique_log.index.name == "artwork_id":
            unique_log = unique_log.reset_index()
        recent_artworks = unique_log.head(tag_log_len)["artwork_id"].tolist()
        artwork_tags_data = self.get_tags_for_artwork_ids(recent_artworks)
        id_tag_time = [
        (artwork_id, tag, unique_log.loc[unique_log["artwork_id"] == artwork_id, "event_time"].values[0])
        for artwork_id, tags in artwork_tags_data.items()
        for tag in tags
        ]

        id_tag_time_df = pd.DataFrame(id_tag_time, columns=["artwork_id", "tags", "event_time"])
        id_tag_time_df["tags"] = id_tag_time_df["tags"].astype(str)  # Ensure 'tags' is string type
        id_tag_time_df = id_tag_time_df.sort_values(by="event_time", ascending=False)
        id_tag_time_df = id_tag_time_df.set_index("artwork_id")  # Set artwork_id as index
        tag_ids = id_tag_time_df["tags"].unique().tolist()
        # Get tag click rates from API
        tag_rate_dict = self.get_tags_for_click_rates(tag_ids)
        tag_rate_df = pd.DataFrame(tag_rate_dict, index=["tag_click_rate"]).T
        # Store tag and type data with rates
        tag_time_count = (
        id_tag_time_df.groupby("tags")
        .agg(event_time=("event_time", "max"), tag_count=("event_time", "size"))
        .join(tag_rate_df, on="tags", how="left")  # Ensure correct join
        )
        # Sort by click rates and event_time, both in descending order
        tag_sorted = tag_time_count.sort_values(
            by=["tag_click_rate", "event_time"], ascending=[False, False]
        )
        # Get type click rates from API
        self.tag_count_all.index = self.tag_count_all.index.astype(str)  # Ensure index is string

        # Fetch type click rates from API
        type_rate_dict = self.get_types_for_click_rates(tag_ids)

        type_rate_df = pd.DataFrame.from_dict(type_rate_dict, orient='index', columns=['type_click_rate'])
        type_time_count = (
        id_tag_time_df.join(self.tag_count_all[['type']], on='tags')
        .groupby('type')
        .agg(
            event_time=("event_time", "max"),
            type_count=("tags", "size")
        )
        .merge(self.tag_count_all.groupby('type').agg(type_count_all=("tag_count_all", "sum")), 
               on='type', how='left')
        .merge(type_rate_df, left_index=True, right_index=True, how='left')
        )

        # Sort by 'type_click_rate' and 'event_time'
        type_sorted = type_time_count.sort_values(
            by=["type_click_rate", "event_time"], ascending=[False, False]
        )

        # Update the class variables
        self.tag_list = tag_sorted.index.tolist()
        self.tag_rate_dict = tag_sorted["tag_click_rate"].to_dict()
        self.type_list = type_sorted.index.tolist()
        self.type_rate_dict = type_sorted["type_click_rate"].to_dict()
        results = {}
        for tag_type in self.type_list:
            tags_of_type = tag_sorted[
                tag_sorted.index.isin(self.tag_count_all[self.tag_count_all['type'] == tag_type].index)
            ]
            top_tags = tags_of_type.head(num_tag)
            results[tag_type] = top_tags["tag_click_rate"].to_dict()

        self.all_list = defaultdict(list)
        for tag_type in self.type_list:
            self.candidates_list = []
            self.tag_list = list(results[tag_type].keys())
            self.loop_tag_rate_dict = results[tag_type]
            self.candidates_tags = []
            for tag in self.tag_list:
                artwork_ids = self.get_artworks_for_tag_id(tag)
                art_tags_data = self.get_tags_for_artwork_ids(artwork_ids)
                art_tag_scores = pd.Series(art_tags_data).apply(
                    lambda tags: sum(
                        self.loop_tag_rate_dict.get(tag, 0) for tag in tags
                    )
                ).sort_values(ascending=False)
                self.candidates_list.append(art_tag_scores.index.tolist())
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
        if not recommended_set: 
            init_tags =  ['Tag: 1'] * len(self.init_list)
            return [self.init_list], [init_tags], len(self.init_list)
        exclude_set = self.interacted_set | recommended_set

        # Create a filtered version of all_list
        filtered_all_list = {}

        for tag_type, artwork_ids in self.all_list.items():
            filtered_artwork_ids = [
                [x for x in ids if x not in exclude_set] for ids in artwork_ids[0]
            ]
            filtered_artwork_ids = [ids for ids in filtered_artwork_ids if ids]

            filtered_tags = [
                tag for i, tag in enumerate(artwork_ids[1]) if any(p not in exclude_set for p in artwork_ids[0][i])
            ]
            # Store the filtered results
            filtered_all_list[tag_type] = [filtered_artwork_ids, filtered_tags]
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
        # Check for duplicates in selected_artworks
        return [selected_artworks], [selected_tags], len(selected_artworks)
