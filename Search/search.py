import os
import shutil
import torch
import open_clip
import faiss

import pandas as pd
import numpy as np

from sentence_transformers import SentenceTransformer
from PIL import Image


DATA_DIR = "../data"
OUTPUT_DIR = "output_minmax"


def e5_search(query, model, index, k):
    query_embedding = model.encode(query, normalize_embeddings=True)
    D, I = index.search(query_embedding[None, :], k)
    return D, I


def clip_search(query, tokenizer, model, index, k):
    query = tokenizer(query)
    query_embedding = model.encode_text(query).numpy()
    query_embedding /= np.linalg.norm(query_embedding, axis=1, keepdims=True)
    D, I = index.search(query_embedding, k)
    return D, I


def save_images(filepath, image_ids, nrow=5):
    # Load images
    images = [Image.open(f"images/{image_id}.jpg") for image_id in image_ids]

    # Calculate the size of the grid
    nrows = (len(images) + nrow - 1) // nrow  # Calculate required number of rows
    max_widths = [0] * nrow
    max_heights = [0] * nrows
    for i, img in enumerate(images):
        row, col = divmod(i, nrow)
        max_widths[col] = max(max_widths[col], img.width)
        max_heights[row] = max(max_heights[row], img.height)

    total_width = sum(max_widths)
    total_height = sum(max_heights)

    # Create a new blank image for the grid
    grid_image = Image.new("RGB", (total_width, total_height))

    # Paste images into the grid
    y_offset = 0
    for row in range(nrows):
        x_offset = 0
        for col in range(nrow):
            if row * nrow + col < len(images):
                grid_image.paste(images[row * nrow + col], (x_offset, y_offset))
            x_offset += max_widths[col]
        y_offset += max_heights[row]

    grid_image.save(filepath)
    print(f"Image saved as {filepath}")


if __name__ == "__main__":
    e5_index_path = os.path.join(DATA_DIR, f"artworks_e5.index")
    # ======================  Create Index  ====================== #
    # e5_embeddings = np.load(os.path.join(DATA_DIR, "search_embeds_e5_v2.npy"))
    # print(e5_embeddings.shape)
    # e5_index = create_faiss_index(e5_embeddings, e5_index_path)

    e5_index = faiss.read_index(e5_index_path)

    clip_index_path = os.path.join(DATA_DIR, f"artworks_clip.index")
    # ======================  Create Index  ====================== #
    # clip_embeddings = np.load(os.path.join(DATA_DIR, "search_embeds_clip_v2.npy"))
    # print(clip_embeddings.shape)
    # clip_index = create_faiss_index(clip_embeddings, clip_index_path)

    clip_index = faiss.read_index(clip_index_path)

    metadata = pd.read_csv(os.path.join(DATA_DIR, "paintings_v2.csv"))
    print(metadata.shape)

    e5_model = SentenceTransformer("intfloat/e5-large-v2")

    clip_model, _, _ = open_clip.create_model_and_transforms(
        "ViT-SO400M-14-SigLIP-384", pretrained="webli"
    )
    clip_tokenizer = open_clip.get_tokenizer("ViT-SO400M-14-SigLIP-384")

    with torch.no_grad(), torch.cuda.amp.autocast():
        for query in [
            "women in blue clothes",
            "Gothic architecture",
            "sport activities",
            "crowd on a beach or a riverbank",
            "Painting of joy",
            "Vincent van Gogh",
            "Vincent Vangogh",
            "people celebrating cultural festivals or traditions",
            "paintings showing agricultural life",
            "Vincent van Gogh",
            "pictures with large areas of red",
            "colorful spring",
            "bold color",
            "pictures containing christian cross",
            "Portraits of historical figures in the Renaissance era",
            "warm, cozy feeling of autumn",
            "cute cats",
            "women with apple",
            "apple still life",
            "16th century",
            "Polish Art",
            "Artist portraits",
            "loneliness and depression",
            "paintings showcase youth and energy",
            "Floral",
            "Vase",
            "Impressionism",
            "Loose brushwork",
            "Baroque Era",
        ]:
            filename = query.replace(" ", "_")

            D, I = e5_search("query: " + query, e5_model, e5_index, 500)
            e5_result = pd.DataFrame({"score": D[0]}, index=I[0])

            D, I = clip_search(query, clip_tokenizer, clip_model, clip_index, 500)
            clip_result = pd.DataFrame({"score": D[0]}, index=I[0])

            result = e5_result.join(
                clip_result, how="inner", lsuffix="_e5", rsuffix="_clip"
            )
            result["score"] = result["score_e5"] + result["score_clip"]
            result = result.join(metadata, how="inner")
            result.sort_values(by="score", ascending=False, inplace=True)
            result.to_csv(os.path.join(OUTPUT_DIR, filename + ".csv"))
            save_images(
                os.path.join(OUTPUT_DIR, filename + ".jpg"),
                result["image_id"].head(25),
            )
