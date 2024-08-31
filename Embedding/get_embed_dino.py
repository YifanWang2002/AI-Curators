import torch
import pandas as pd
from PIL import Image
import numpy as np
from transformers import AutoProcessor, CLIPModel, AutoImageProcessor, AutoModel
from tqdm import tqdm  # Import tqdm for the progress bar

# Load data
df = pd.read_csv("../data/paintings_v2.csv")

# Load the DINO model and its pre-trained image processor
model_name = "facebook/dinov2-base"
processor = AutoImageProcessor.from_pretrained("facebook/dinov2-base")
model = AutoModel.from_pretrained(model_name)

# Set up processing parameters
batch_size = 8
image_embeddings = []

with torch.no_grad():
    # Initialize tqdm progress bar
    for start_index in tqdm(range(0, len(df), batch_size), desc="Processing Images"):
        image_ids = df["image_id"][start_index : start_index + batch_size].tolist()
        images = [
            Image.open(f"images/{image_id}.jpg").convert("RGB")
            for image_id in image_ids
        ]
        inputs = processor(images=images, return_tensors="pt")

        # Move input tensors to the same device as the model
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        outputs = model(**inputs)

        # Extract embeddings, typically the last hidden state
        embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
        image_embeddings.append(embeddings)

# Finalize embeddings
image_embeddings = np.concatenate(image_embeddings)
image_embeddings /= np.linalg.norm(image_embeddings, axis=1, keepdims=True)

# Save embeddings
np.save("../data/embeds_dino.npy", image_embeddings)
