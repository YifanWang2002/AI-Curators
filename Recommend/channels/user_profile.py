import os
import json
import faiss
import itertools
import numpy as np
import pandas as pd


class UserProfileChannel:

    def __init__(self, metadata, user_id, configs):
        self.meta_data = metadata
        self.user_id = user_id
        self.configs = configs
        self.num_per_page = self.configs["num_per_page"]
        self.tag_embedding = np.load(self.configs["tag_emb_path"])
        self.tag_index = self.get_tag_index()
        self.tag_name2id_mapping, self.tag_id2name_mapping = self.get_tag_mapping()
        self.tag_to_object_mapping = json.load(open(self.configs["tag_to_object_mapping_path"], "r", encoding="utf-8"))
        self.pre_survey, self.pre_survey_tags_type = self.get_pre_survey(self.user_id, self.configs["pre_survey_dir"])
        self.interacted_set = set()

    def get_tag_index(self):
        if os.path.exists(self.configs["tag_emb_index_path"]):
            return faiss.read_index(self.configs["tag_emb_index_path"])
        else:
            tag_index = faiss.IndexFlatL2(self.tag_embedding.shape[1])
            tag_index.add(self.tag_embedding)
            faiss.write_index(tag_index, self.configs["tag_emb_index_path"])
            return tag_index
        
    def get_tag_mapping(self):
        tag_name2id_mapping = {}
        tag_id2name_mapping = {}
        tag_count_type = pd.read_csv(self.configs["tag_count_type_path"])
        for i, row in tag_count_type.iterrows():
            tag_name2id_mapping[row["tag"]] = {"tag_no": i, "count": row["count"], "type": row["type"]}
            tag_id2name_mapping[i] = row["tag"]
        return tag_name2id_mapping, tag_id2name_mapping

    def get_interacted_set(self, user_id, updated):
        # TODO: Load interacted set from the database
        if updated:
            with open(os.path.join(self.configs["interacted_dir"], f"interacted_{user_id}.txt"), "r", encoding="utf-8") as f:
                self.interacted_set = set([int(idx) for idx in f.read().splitlines()])
        return self.interacted_set

    def get_pre_survey(self, user_id, survey_dir):
        # TODO: Load pre-survey data from the database
        with open(os.path.join(survey_dir, f"{user_id}.json"), "r", encoding="utf-8") as reader:
            pre_survey = json.load(reader)
        pre_survey_tags_type = sorted(pre_survey.keys())
        return pre_survey, pre_survey_tags_type
    
    def get_recs_list_by_tags(self, num_per_tag_type):
        recs_list_by_tags = []
        tags_no = []
        recs_tags_type = []
        for tag_type in self.pre_survey_tags_type:
            tag_name = self.pre_survey[tag_type]["value"]
            if tag_name not in self.tag_name2id_mapping:
                continue
            else:
                recs_tags_type.append(tag_type)
                tag_no = self.tag_name2id_mapping[tag_name]["tag_no"]
                tags_no.append(tag_no)
        if len(tags_no) == 0:
            return recs_list_by_tags
        tag_embeddings = self.tag_embedding[tags_no]
        D, I = self.tag_index.search(tag_embeddings, num_per_tag_type)
        recs_tag_list = []
        for i in range(len(I)):
            recs_tag_list.append([(I[i, j], D[i, j]) for j in range(len(I[i])) if j != 0])
        recs_object_list = []
        for recs in recs_tag_list:
            objects = [self.tag_to_object_mapping[self.tag_id2name_mapping[x[0]]] for x in recs if self.tag_id2name_mapping[x[0]] in self.tag_to_object_mapping]
            recs_object_list.append(list(set(itertools.chain(*objects))))
        return recs_object_list, recs_tags_type
    
    def personalized_tags_recs(self, exclude_set):
        num_per_tag_type = self.num_per_page
        recs_list, recs_tags_type = self.get_recs_list_by_tags(num_per_tag_type)
        filtered_recs_list = [
            [x for x in recs if x not in exclude_set] for recs in recs_list
        ]
        while sum(len(recs) < self.num_per_page for recs in filtered_recs_list) == len(self.pre_survey_tags_type):
            num_per_tag_type += self.num_per_page
            recs_list, recs_tags_type = self.get_recs_list_by_tags(num_per_tag_type)
            filtered_recs_list = [
                [x for x in recs if x not in exclude_set] for recs in recs_list
            ]
        recs_hash = {}
        for i, x in enumerate(recs_tags_type):
            recs_hash.update({k: f"Profile Tag: {x}" for k in filtered_recs_list[i]})
        return list(recs_hash.keys()), list(recs_hash.values()), len(recs_hash)
    
    def personalized_queries_recs(self, exclude_set):
        return [], [], 0
    
    def __call__(self, context_info, recommended_set):
        exclude_set = self.get_interacted_set(self.user_id, context_info["behavior_updated"]) | recommended_set
        
        tags_recs_list, tags_recs_names, len_tags = self.personalized_tags_recs(exclude_set)
        queries_recs_list, queries_recs_names, len_queries = self.personalized_queries_recs(exclude_set)
        return [tags_recs_list], [tags_recs_names], len_tags
