import os
import faiss
import numpy as np


DATA_DIR = "data"


def create_faiss_index(embeddings, index_path):
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, index_path)

    return index


e5_index_path = os.path.join(DATA_DIR, f"artworks_e5.index")
e5_embeddings = np.load(os.path.join(DATA_DIR, "search_embeds_e5_v2.npy"))
print(e5_embeddings.shape)
e5_index = create_faiss_index(e5_embeddings, e5_index_path)

clip_index_path = os.path.join(DATA_DIR, f"artworks_clip.index")
clip_embeddings = np.load(os.path.join(DATA_DIR, "search_embeds_clip_v2.npy"))
print(clip_embeddings.shape)
clip_index = create_faiss_index(clip_embeddings, clip_index_path)

embeddings = np.load(os.path.join(DATA_DIR, f"embeds_dino.npy"))
print(embeddings.shape)

index_path = os.path.join(DATA_DIR, f"artworks_dino.index")
index = create_faiss_index(embeddings, index_path)
