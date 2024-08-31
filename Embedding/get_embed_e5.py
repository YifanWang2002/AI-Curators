import pandas as pd
import numpy as np

from sentence_transformers import SentenceTransformer

df = pd.read_csv("../data/search_e5.csv")

model = SentenceTransformer("intfloat/e5-large-v2")

batch_size = 2
all_embeddings = []

for start_index in range(0, len(df), batch_size):
    batch_documents = df["overall"][start_index : start_index + batch_size].tolist()
    batch_embeddings = model.encode(batch_documents, normalize_embeddings=True)
    all_embeddings.extend(batch_embeddings)

embeds = np.stack(all_embeddings)
np.save("../data/search_embeds.npy", embeds)
