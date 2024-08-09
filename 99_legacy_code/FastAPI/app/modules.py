# Import Modules
from models import profileChoiceModel, profileQuestionModel, allProfileQuestionModel
import pandas as pd
import random
from pathlib import Path

# Get CSV file path
current_dir = Path(__file__).parent
csv_path = current_dir.parent / 'data' / 'art_metadata.csv'


# Data Preprocessing

def create_all_profile_questions(n_questions: int = 10):
    all_questions = []
    art_database = pd.read_csv(csv_path)
    for q_id in range(n_questions):
        selected_images = art_database.sample(n=4)
        choices = []

        for idx, row in enumerate(selected_images.itertuples(), start=1):
            choice = profileChoiceModel(
                # choice_id=idx,
                image_id=row.ID,
                image_title=row.TITLE,
                )
            choices.append(choice)

        question = profileQuestionModel(question_id=q_id, choices=choices)
        all_questions.append(question)

    return allProfileQuestionModel(questions=all_questions)


# ML Model
import torch
from transformers import BertTokenizer, BertModel
import faiss
import numpy as np
import tqdm
import os

def get_bert_embedding(text, model_name: str = "bert-large-uncased", model_dir = "./embedding_model",max_length: int = 512):
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)  # Create the directory if it doesn't exist
        # Download and save the tokenizer and model
        tokenizer = BertTokenizer.from_pretrained(model_name)
        model = BertModel.from_pretrained(model_name)
        tokenizer.save_pretrained(model_dir)
        model.save_pretrained(model_dir)
    else:
        # Load the tokenizer and model from the local directory
        tokenizer = BertTokenizer.from_pretrained(model_dir)
        model = BertModel.from_pretrained(model_dir)
    
    chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    embedding = []
    for chunk in chunks:
        input_ids = tokenizer.encode(chunk, add_special_tokens=True, return_tensors='pt')
        with torch.no_grad():
            outputs = model(input_ids)
        embedding.append(outputs[0].mean(dim=1).squeeze().numpy())
    # Return the average of the embeddings
    return np.mean(embedding, axis=0)

def process_dataframe(df, text_column="analysis", embedding_column_prefix="emb_", output_csv="data/art_metadata_embedding.csv"):
    embedding_size = 1024  # Adjust based on your model's embedding size
    embedding_columns = [f"{embedding_column_prefix}{i}" for i in range(embedding_size)]

    # Load existing data or initialize DataFrame with embedding columns
    if os.path.exists(output_csv) and os.path.getsize(output_csv) > 0:
        existing_df = pd.read_csv(output_csv)
    else:
        # Create a DataFrame with additional embedding columns initialized as NaN
        for col in embedding_columns:
            df[col] = float('nan')
        existing_df = df

    # Identify rows with missing embeddings
    missing_embeddings = existing_df[embedding_columns].isna().any(axis=1)

    for idx in tqdm.tqdm(df.index):
        if missing_embeddings[idx]:
            text = df.loc[idx, text_column]
            # Get the embedding for the text
            embedding = get_bert_embedding(text)
            # Update the row with the new embeddings
            existing_df.loc[idx, embedding_columns] = list(embedding)
            # Save the updated DataFrame to the CSV file
            existing_df.to_csv(output_csv, index=False)


def create_faiss_index(df, embedding_column_prefix="emb_", faiss_index_path="embedding_model/faiss_index.pickle"):
    embedding_columns = [col for col in df.columns if col.startswith(embedding_column_prefix)]
    embeddings = df[embedding_columns].to_numpy(dtype='float32')
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    if faiss_index_path:
        faiss.write_index(index, faiss_index_path)
    
    return index

def retrieve_similar_items(embedding, faiss_index, top_k=5):
    distances, indices = faiss_index.search(np.array([embedding]), top_k)
    return indices[0]

def get_dataframe_rows(df, indices):
    return df.iloc[indices]

