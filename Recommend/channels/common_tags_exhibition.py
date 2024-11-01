
import random
import numpy as np
import pandas as pd
from collections import defaultdict
from Recommend.api.data import get_clicked_exhibitions_by_user, get_exhibitions_by_tag_id, get_all_tags, get_tags_by_exhibition_ids, get_tags_click_rates, get_type_click_rates

class CommonTagsChannel:
    def __init__(self, configs):
        self.configs = configs
        self.tag_count_all = self.load_tag_count()
        self.interacted_set = set()
        self.tag_list = [1, 2]
        self.all_list = defaultdict(list)

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

    def get_clicked_exhibitions_for_user(self, user_id):
        return self.fetch_api_data(lambda: get_clicked_exhibitions_by_user(user_id), 
                                   f"Failed to fetch exhibitions for user_id {user_id}")


    def get_exhibitions_for_tag_id(self, tag_id):
        """Fetch exhibitions for a specific tag ID."""
        return self.fetch_api_data(lambda: get_exhibitions_by_tag_id(tag_id), 
                                   f"Failed to fetch exhibitions for tag_id {tag_id}")
    def get_tags_for_exhibition_ids(self, exhibition_ids):
        return self.fetch_api_data(lambda: get_tags_by_exhibition_ids(exhibition_ids), 
                                   f"Failed to fetch tags for exhibition IDs {exhibition_ids}")

    def get_tags_for_click_rates(self, tag_ids):
        return self.fetch_api_data(lambda: get_tags_click_rates(tag_ids), 
                                   f"Failed to fetch tags for exhibition IDs {tag_ids}")
    def get_types_for_click_rates(self, tag_ids):
        return self.fetch_api_data(lambda: get_type_click_rates(tag_ids), 
                                   f"Failed to fetch tags for exhibition IDs {tag_ids}")

    def update_data(self, unique_log, tag_log_len, num_tag, interacted_set):
        user_exhibitions = self.get_clicked_exhibitions_for_user(4)
        unique_log = pd.DataFrame(user_exhibitions)[["exhibition_id", "event_time"]]
        unique_log["exhibition_id"] = unique_log["exhibition_id"].astype(float).astype(int)
        print("unique_log is,", unique_log)
        recent_exhibitions = unique_log.head(tag_log_len)["exhibition_id"].tolist()
        exhibition_tags_data = self.get_tags_for_exhibition_ids(recent_exhibitions)
        print("exhibition_tags_data is", exhibition_tags_data)
        id_tag_time = []
        for exhibition_id, tags in exhibition_tags_data.items():
            print("exhibition_id is", exhibition_id)
            print("exhibition_id type is", type(exhibition_id))
    
            unique_log["exhibition_id"] = unique_log["exhibition_id"].astype(str)
            print("unique_log['exhibition_id'] contents:", unique_log["exhibition_id"].tolist())
            print("Type of unique_log['exhibition_id']:", type(unique_log["exhibition_id"]))
            print("Data type of each element:", unique_log["exhibition_id"].apply(type).tolist())

            event_time = unique_log.loc[unique_log["exhibition_id"] == exhibition_id, "event_time"].values[0]
            for tag in tags:
                id_tag_time.append((exhibition_id, tag, event_time))
        id_tag_time_df = pd.DataFrame(id_tag_time, columns=["exhibition_id", "tags", "event_time"])
        id_tag_time_df["tags"] = id_tag_time_df["tags"].astype(str)  # Ensure 'tags' is string type
        id_tag_time_df = id_tag_time_df.sort_values(by="event_time", ascending=False)
        id_tag_time_df = id_tag_time_df.set_index("exhibition_id")  # Set exhibition_id as index

        # print("API-based id_tag_time:")
        # print(id_tag_time_df)

        # print("self.tag_count_all", self.tag_count_all)
        tag_ids = id_tag_time_df["tags"].unique().tolist()
        # print("tag_ids is", tag_ids)
        # Get tag click rates from API
        tag_rate_dict = self.get_tags_for_click_rates(tag_ids)
        tag_rate_df = pd.DataFrame(tag_rate_dict, index=["tag_click_rate"]).T
        tag_rate_df.index = tag_rate_df.index.astype(str)  # Convert index to string

        # print("tag_rate_dict is", tag_rate_dict)

        # Store tag and type data with rates
        tag_time_count = (
        id_tag_time_df.groupby("tags")
        .agg(event_time=("event_time", "max"), tag_count=("event_time", "size"))
        .join(tag_rate_df, on="tags", how="left")  # Ensure correct join
        )
    
        # print("tag_time_count  is", tag_time_count)
         # Sort by click rates and event_time, both in descending order
        tag_sorted = tag_time_count.sort_values(
            by=["tag_click_rate", "event_time"], ascending=[False, False]
        )
        # print("tag_sorted is", tag_sorted)

        # Get type click rates from API
        id_tag_time_df["tags"] = id_tag_time_df["tags"].astype(str)
        self.tag_count_all.index = self.tag_count_all.index.astype(str)  # Ensure index is string

        # Fetch type click rates from API
        type_rate_dict = self.get_types_for_click_rates(tag_ids)
        # print("type_rate_dict is", type_rate_dict)

        type_rate_df = pd.DataFrame.from_dict(type_rate_dict, orient='index', columns=['type_click_rate'])
        type_rate_df.index = type_rate_df.index.astype(str)  # Ensure the index is string

        type_time_count = (
            id_tag_time_df.join(self.tag_count_all[['type']], on='tags')
            .groupby('type')
            .agg(
                event_time=("event_time", "max"),  # Most recent event_time for each type
                type_count=("tags", "size")      # Count the number of tags per type
            )
            .join( 
                self.tag_count_all.groupby('type').agg(type_count_all=("tag_count_all", "sum")),
                on='type'
            )
            .join(  
                type_rate_df, on='type'
            )
        )

        # print("type_time_count:")
        # print(type_time_count)

        # Sort by 'type_click_rate' and 'event_time'
        type_sorted = type_time_count.sort_values(
            by=["type_click_rate", "event_time"], ascending=[False, False]
        )

        # print("type_sorted:")
        # print(type_sorted)

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
        # print("results are,", results)

        self.all_list = defaultdict(list)
        for tag_type in self.type_list:
            self.candidates_list = []
            self.tag_list = list(results[tag_type].keys())
            self.loop_tag_rate_dict = results[tag_type]
            self.candidates_tags = []
            for tag in self.tag_list:
                exhibition_ids = self.get_exhibitions_for_tag_id(tag)
                art_tags_data = self.get_tags_for_exhibition_ids(exhibition_ids)
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
            init_list = random.sample([str(i) for i in range(100)], 50)
            init_tags =  ['Tag: 1'] * len(init_list)
            return [init_list], [init_tags], len(init_list)
        exclude_set = self.interacted_set | recommended_set

        # Create a filtered version of all_list
        filtered_all_list = {}

        for tag_type, exhibition_ids in self.all_list.items():
            filtered_exhibition_ids = [
                [x for x in ids if x not in exclude_set] for ids in exhibition_ids[0]
            ]
            filtered_exhibition_ids = [ids for ids in filtered_exhibition_ids if ids]

            filtered_tags = [
                tag for i, tag in enumerate(exhibition_ids[1]) if any(p not in exclude_set for p in exhibition_ids[0][i])
            ]
            # Store the filtered results
            filtered_all_list[tag_type] = [filtered_exhibition_ids, filtered_tags]
       
        exhibition_weights = []
        guaranteed_exhibitions = []
        total_exhibitions = self.configs["num_per_page"]

        for type_key, (exhibition_groups, tags) in filtered_all_list.items():
            type_weight = self.type_rate_dict[type_key]
            
            type_exhibitions_with_scores = []

            for idx, exhibition_group in enumerate(exhibition_groups):
                tag = tags[idx]  # Get the corresponding tag for this group
                # print("self.tag_rate_dict is", self.tag_rate_dict)
                tag_weight = self.tag_rate_dict[tag.split(": ")[1]]  # Get the tag's weight

                for exhibition in exhibition_group:
                    blended_weight = self.calculate_weight(tag_weight, type_weight, 0.7)
                    type_exhibitions_with_scores.append((exhibition, tag, type_key, blended_weight))
            
            highest_scored_exhibition = max(type_exhibitions_with_scores, key=lambda x: x[3])
            guaranteed_exhibitions.append(highest_scored_exhibition)

            exhibition_weights.extend(type_exhibitions_with_scores)

        remaining_exhibition_weights = [
            aw for aw in exhibition_weights if aw[0] not in [g[0] for g in guaranteed_exhibitions]
        ]

        remaining_exhibition_weights.sort(key=lambda x: x[3], reverse=True)

        num_remaining_exhibitions = total_exhibitions - len(guaranteed_exhibitions)
        selected_remaining_exhibitions = remaining_exhibition_weights[:num_remaining_exhibitions]

        final_exhibition_selection = guaranteed_exhibitions + selected_remaining_exhibitions

        final_exhibition_selection.sort(key=lambda x: x[3], reverse=True)

       # Deduplicate selected exhibitions using a dictionary to remove duplicates by exhibition ID
        unique_exhibitions = list({exhibition: (tag, type_key, weight)
                                for exhibition, tag, type_key, weight in final_exhibition_selection}.items())

        # Extract the exhibitions, tags, types, and weights properly
        selected_exhibitions = [exhibition for exhibition, _ in unique_exhibitions]
        selected_tags = [tag for _, (tag, _, _) in unique_exhibitions]
        selected_types = [type_key for _, (_, type_key, _) in unique_exhibitions]
        return [selected_exhibitions], [selected_tags], len(selected_exhibitions)