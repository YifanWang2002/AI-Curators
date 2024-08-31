import torch
import torch.nn.functional as F
import open_clip
import pandas as pd
import numpy as np
from PIL import Image


df = pd.read_csv("../data/paintings_v1.csv")

model, _, preprocess = open_clip.create_model_and_transforms(
    "ViT-SO400M-14-SigLIP-384", pretrained="webli"
)
# tokenizer = open_clip.get_tokenizer("ViT-SO400M-14-SigLIP-384")


batch_size = 8
image_embeddings = []

with torch.no_grad(), torch.cuda.amp.autocast():
    for start_index in range(0, len(df), batch_size):
        image_ids = df["image_id"][start_index : start_index + batch_size].tolist()
        images = torch.stack(
            [preprocess(Image.open(f"images/{image_id}.jpg")) for image_id in image_ids]
        )
        image_embeddings.append(model.encode_image(images).cpu().numpy())


image_embeddings = np.concatenate(image_embeddings)
image_embeddings /= np.linalg.norm(image_embeddings, axis=1, keepdims=True)
np.save("../data/search_embeds_clip.npy", image_embeddings)
