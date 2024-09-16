import os
import json
import faiss
import random
import numpy as np


class UserProfileChannel:

    def __init__(self, user_id, configs):
        self.user_id = user_id
        self.configs = configs
        self.num_per_page = self.configs["num_per_page"]
        self.tag_embedding = np.load(self.configs["tag_embedding_path"])
        self.tag_index = faiss.read_index(self.configs["tag_index_path"])
        self.pre_survey, self.pre_survey_tags = self.load_pre_survey(self.user_id, self.configs["pre_survey_dir"])
        self.interacted_set = set()

    def get_interacted_set(self, user_id, updated):
        # TODO: Load interacted set from the database
        if updated:
            with open(os.path.join(self.configs["interacted_dir"], f"interacted_{user_id}.txt"), "r", encoding="utf-8") as f:
                self.interacted_set = set(f.read().splitlines())
        return self.interacted_set

    def load_pre_survey(self, user_id, survey_dir):
        # TODO: Load pre-survey data from the database
        with open(os.path.join(survey_dir, f"{user_id}.json"), "r", encoding="utf-8") as reader:
            pre_survey = json.load(reader)
        pre_survey_tags = sorted(self.pre_survey.values())
        return pre_survey, pre_survey_tags
    
    def get_recs_list_by_tags(self, channel, num_per_tag_type):
        recs_list_by_tags = []
        tag_no = self.pre_survey_tags[channel]
        tag_embeddings = self.tag_embedding[tag_no]
        D, I = self.tag_index.search(tag_embeddings, num_per_tag_type)
        recs_list_by_tags[channel] = I[:, :].tolist()
        return recs_list_by_tags
    
    def personalized_tags_recs(self, exclude_set):
        num_per_tag_type = self.num_per_page
        recs_list = []
        for channel in self.pre_survey_tags:
            recs_list.append(self.get_recs_list_by_tags(channel, num_per_tag_type))
        filtered_recs_list = [
            [x for x in recs if x not in exclude_set] for recs in recs_list
        ]
        while sum(len(recs) < self.num_per_page for recs in filtered_recs_list) < self.num_per_page:
            num_per_tag_type += self.num_per_page
            for i, channel in enumerate(self.pre_survey_tags):
                if len(recs_list[i]) < self.num_per_page:
                    recs_list[i] = self.get_recs_list_by_tags(channel, self.num_per_page)
            filtered_recs_list = [
                [x for x in recs if x not in exclude_set] for recs in recs_list
            ]
        tag_channel_names = [f"Tag Channel: {x}" for x in self.pre_survey_tags]
        print(tag_channel_names)
        return filtered_recs_list, tag_channel_names, len(filtered_recs_list)
    
    def personalized_queries_recs(self, exclude_set):
        return [], [], 0
    
    def __call__(self, context_info, recommended_set):
        exclude_set = self.get_interacted_set(self.user_id, context_info["behavior_updated"]) | recommended_set
        
        tags_recs_list, tags_recs_names, len_tags = self.personalized_tags_recs(exclude_set)
        queries_recs_list, queries_recs_names, len_queries = self.personalized_queries_recs(exclude_set)
        return tags_recs_list + queries_recs_list, tags_recs_names + queries_recs_names, len_tags + len_queries
