import os
import ast
import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

pd.set_option("display.width", None)

DATA_DIR = "../data"


def create_faiss_index(embeddings, index_path):
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, index_path)

    return index


def search(query_embedding, index, k):
    D, I = index.search(query_embedding[None, :], k)
    return D, I


def safe_literal_eval(x, col):
    try:
        return ast.literal_eval(x)
    except:
        return dict() if col == "main_objects" else []


if __name__ == "__main__":
    df = pd.read_csv(os.path.join(DATA_DIR, "paintings_v2.csv"))
    lit_columns = [
        "style_tags",
        "theme_tags",
        "main_objects",
        "other_objects",
        "movement",
    ]
    for col in lit_columns:
        df[col] = df[col].apply(lambda x: safe_literal_eval(x, col))
    print(df.shape)
    df.dropna(subset=lit_columns, inplace=True)
    print(df.shape)
    df["object_tags"] = df.apply(
        lambda row: list(row["main_objects"].keys()) + row["other_objects"], axis=1
    )

    # for col in ["style_tags", "theme_tags", "object_tags"]:
    #     tag_series = df[col].explode().str.capitalize()
    #     tag_series.value_counts().sort_values(ascending=False).to_csv(
    #         f"data/{col}_value_counts.csv"
    #     )
    tags = []
    for col in ["style_tags", "theme_tags", "object_tags", "movement"]:
        tmp = df[col].explode().reset_index(name="tag")
        tmp["type"] = col
        tags.append(tmp)

    tags = pd.concat(tags).dropna()

    # filter out date-related tags
    tags = tags[~tags["tag"].str.contains(r"century|\d+", case=False)]
    tags["tag"] = (
        tags["tag"]
        .str.lower()
        .replace("_", " ")
        .replace(
            r" (application|use|influence|art|painting|men|women|man|woman)$",
            "",
            regex=True,
        )
        .replace(r"impressionist(ic)?", "impressionism", regex=True)
        .replace(r"mannerist", "mannerism", regex=True)
        # .replace(r"(color palette|palette|tones)$", "color", regex=True)
        # .replace(r"portrait$", "portraiture", regex=True)
        .str.title()
    )

    print(tags)

    blacklist = [
        "Art",
        "Texture",
        "Textured",
        "Light",
        "Identity",
        "Beauty",
        "Brushwork",
        "Color",
        "Subject",
    ]
    tags = tags[~tags["tag"].isin(blacklist)]
    tag_counts = tags["tag"].value_counts().sort_values(ascending=False)
    unique_tags = tag_counts.index.values

    print(len(unique_tags))

    index_path = os.path.join(DATA_DIR, f"tag_e5.index")

    # model = SentenceTransformer("intfloat/e5-large-v2")
    # tag_embeddings = []
    # batch_size = 4
    # for start_index in range(0, len(unique_tags), batch_size):
    #     batch_documents = unique_tags[start_index : start_index + batch_size]
    #     batch_embeddings = model.encode(batch_documents, normalize_embeddings=True)
    #     tag_embeddings.extend(batch_embeddings)

    # tag_embeddings = np.stack(tag_embeddings)
    # np.save(os.path.join(DATA_DIR, "tag_embeddings.npy"), tag_embeddings)

    tag_embeddings = np.load(os.path.join(DATA_DIR, "tag_embeddings.npy"))
    index = create_faiss_index(tag_embeddings, index_path)

    synonyms_list = []
    scores_list = []
    str_list = []
    for tag_embed in tag_embeddings:
        D, I = search(tag_embed, index, 20)
        synonyms_list.append(unique_tags[I[0][1:]])
        scores_list.append(D[0][1:])
        str_list.append(
            ", ".join(unique_tags[i] + ":" + str(d) for d, i in zip(D[0], I[0]))
        )
    print(len(synonyms_list))

    tag_counts_df = tag_counts.reset_index()
    tag_counts_df["synonyms"] = str_list
    tag_counts_df.to_csv(os.path.join(DATA_DIR, "synonyms.csv"), index=False)

    visited = set()
    tag_mapping = dict()

    for tag, synonyms, scores in zip(unique_tags, synonyms_list, scores_list):
        for curr_tag, curr_score in zip(synonyms, scores):
            if (
                curr_score > 0.95
                and tag_counts.loc[curr_tag] < 8
                and curr_tag not in visited
                and curr_tag != tag
                and curr_tag not in tag_mapping
            ):
                root_tag = tag
                while root_tag in tag_mapping:
                    root_tag = tag_mapping[root_tag]
                tag_mapping[curr_tag] = root_tag
        visited.add(tag)

    pd.DataFrame({"Source": tag_mapping.keys(), "Target": tag_mapping.values()}).to_csv(
        os.path.join(DATA_DIR, "tag_mapping.csv"), index=False
    )
    tags["tag"] = tags["tag"].replace(tag_mapping)
    tag_counts = tags["tag"].value_counts().sort_values(ascending=False)
    tag_counts.to_csv(os.path.join(DATA_DIR, "tags_replaced_count.csv"))

    def get_type(x):
        s = set(x.values)
        for tag in ["movement", "style_tags"]:
            if tag in s:
                return tag
        return x.mode()[0]

    tag_types = tags.groupby("tag")["type"].agg(get_type).reset_index()

    tags = tags[["index", "tag"]].drop_duplicates()

    tag_counts = tags["tag"].value_counts().sort_values(ascending=False).reset_index()

    tag_count_type = pd.merge(tag_counts, tag_types, on="tag")
    tag_count_type = tag_count_type[
        (tag_count_type["type"] == "style_tags") & (tag_count_type["count"] >= 8)
        | (tag_count_type["type"] == "theme_tags") & (tag_count_type["count"] >= 8)
        | (tag_count_type["type"] == "object_tags") & (tag_count_type["count"] >= 8)
        | (tag_count_type["type"] == "movement") & (tag_count_type["count"] >= 8)
    ]
    tag_count_type.to_csv(os.path.join(DATA_DIR, "tag_count_type.csv"), index=False)
    tags = tags[tags["tag"].isin(tag_count_type["tag"])]
    tags.to_csv(os.path.join(DATA_DIR, "tags.csv"), index=False)
    for col in [
        "style_tags",
        "theme_tags",
        "object_tags",
        "movement",
    ]:
        tag_counts = tag_count_type[tag_count_type["type"] == col].to_csv(
            os.path.join(DATA_DIR, col + ".csv"), index=False
        )

    tags = tags.groupby("index")["tag"].agg(list)

    df = df.join(tags)
    df.rename(columns={"tag": "tags"}, inplace=True)
    df["tags"] = df["tags"].apply(lambda x: x if isinstance(x, list) else [])
    df.to_csv(os.path.join(DATA_DIR, "tags_replaced.csv"))
