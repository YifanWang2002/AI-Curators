import os


class RandomRecChannel:

    def __init__(self, configs, metadata):
        self.metadata = metadata
        self.configs = configs
        self.num_per_page = self.configs["num_per_page"]
        self.interacted_set = set()

    def get_interacted_set(self, user_id, updated):
        # TODO: Load interacted set from the database
        if updated:
            with open(os.path.join(self.configs["interacted_dir"], f"interacted_{user_id}.txt"), "r", encoding="utf-8") as f:
                self.interacted_set = self.interacted_set | set(f.read().splitlines())
        return self.interacted_set

    def __call__(self, user_id, context_info, recommended_set):
        exclude_set = self.get_interacted_set(user_id, context_info["behavior_updated"]) | recommended_set
        candidates = self.metadata.drop(exclude_set)

        seed = user_id + context_info["timestamp"]
        random_recs_list = candidates.sample(n=self.num_per_page, random_state=seed).index.tolist()

        return random_recs_list, ["Random"] * len(random_recs_list), len(random_recs_list)
