import os
import ast
import faiss
import numpy as np
import pandas as pd
import torch
import open_clip

pd.set_option("display.width", None)

DATA_DIR = "../new_data"


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
    df = pd.read_csv(os.path.join(DATA_DIR, "artwork_with_gpt.csv"))

    tag_columns = [
        "style_tags",
        "theme_tags",
        "main_objects",
        "other_objects",
        "movements",
    ]
    for col in tag_columns:
        df[col] = df[col].apply(lambda x: safe_literal_eval(x, col))

    df["object_tags"] = df.apply(
        lambda row: list(row["main_objects"].keys()) + row["other_objects"], axis=1
    )

    tags = []
    for col in ["style_tags", "theme_tags", "object_tags", "movements"]:
        tmp = df[col].explode().reset_index(name="tag")
        tmp["type"] = col
        tags.append(tmp)

    tags = pd.concat(tags).dropna()

    # filter out date-related tags
    tags = tags[~tags["tag"].str.contains(r"century|\d+", case=False)]
    tags["tag"] = tags["tag"].str.lower().str.replace("_", " ").str.title()

    # tag_count = tags["tag"].value_counts().sort_values(ascending=False)
    # tag_count.to_csv(os.path.join(DATA_DIR, "tag_count.csv"))

    unique_tags = tag_count.index.to_list()

    # # Get Tag Embeddings

    # model, _, _ = open_clip.create_model_and_transforms(
    #     "ViT-SO400M-14-SigLIP-384", pretrained="webli"
    # )
    # tokenizer = open_clip.get_tokenizer("ViT-SO400M-14-SigLIP-384")

    # tag_embeddings = []
    # batch_size = 8
    # with torch.no_grad(), torch.cuda.amp.autocast():
    #     for start_index in range(0, len(unique_tags), batch_size):
    #         tags = tokenizer(unique_tags[start_index : start_index + batch_size])
    #         tags_embedding = model.encode_text(tags).numpy()
    #         tags_embedding /= np.linalg.norm(tags_embedding, axis=1, keepdims=True)
    #         tag_embeddings.extend(tags_embedding)

    # tag_embeddings = np.stack(tag_embeddings)
    # np.save(os.path.join(DATA_DIR, "all_tag_embeddings.npy"), tag_embeddings)

    tag_embeddings = np.load(os.path.join(DATA_DIR, "all_tag_embeddings.npy"))

    # NOTE: unique_tags is already sorted in the descending order of frequency
    # NOTE: tag_embeddings and unique_tags have corresponding orders

    # Outer loop: keyword a, from the least frequent keyword to the most frequent keyword;
    # Inner loop: keyword b, from the most frequent keyword to the element just more frequent than a.
    # If a is very similar to b, map a to b.
    tag_mapping = dict()
    for i in range(len(unique_tags) - 1, -1, -1):
        for j in range(i):
            if np.dot(tag_embeddings[i], tag_embeddings[j]) > 0.94:
                tag_mapping[unique_tags[i]] = unique_tags[j]
                print(unique_tags[i], unique_tags[j])

    pd.DataFrame({"Source": tag_mapping.keys(), "Target": tag_mapping.values()}).to_csv(
        os.path.join(DATA_DIR, "tag_mapping.csv"), index=False
    )
    tags["tag"] = tags["tag"].replace(tag_mapping)

    # Get the type for each tag

    def get_type(x):
        s = set(x.values)
        for tag in ["movement", "style_tags"]:
            if tag in s:
                return tag
        return x.mode()[0]

    tag_types = tags.groupby("tag")["type"].agg(get_type).reset_index()

    tags = tags[["index", "tag"]].drop_duplicates()
    tag_count = tags["tag"].value_counts().sort_values(ascending=False).reset_index()
    tag_count_type = pd.merge(tag_count, tag_types, on="tag")
    tag_count_type = tag_count_type[
        (tag_count_type["type"] == "style_tags") & (tag_count_type["count"] >= 8)
        | (tag_count_type["type"] == "theme_tags") & (tag_count_type["count"] >= 8)
        | (tag_count_type["type"] == "object_tags") & (tag_count_type["count"] >= 8)
        | (tag_count_type["type"] == "movement") & (tag_count_type["count"] >= 8)
    ]
    tag_count_type.to_csv(os.path.join(DATA_DIR, "tag_count_type.csv"), index=False)

    # Save the tag embeddings in the same order as the entries in tag_count_type.csv

    tag_embeddings = np.stack(
        [tag_embeddings[unique_tags.index(tag)] for tag in tag_count_type["tag"]]
    )
    np.save(os.path.join(DATA_DIR, "tag_embeddings.npy"), tag_embeddings)

    # Save the tags together with original columns

    tags = tags.groupby("index")["tag"].agg(list)
    df = df.join(tags)
    df.rename(columns={"tag": "tags"}, inplace=True)
    df["tags"] = df["tags"].apply(lambda x: x if isinstance(x, list) else [])
    df.to_csv(os.path.join(DATA_DIR, "artwork_with_tags.csv"))
