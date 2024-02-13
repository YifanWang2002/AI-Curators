from fastapi import FastAPI, HTTPException
from typing import List
from pydantic import BaseModel
from models import allProfileQuestionModel, allProfileResponseModel
from modules import *
from pathlib import Path

# Get CSV file path
current_dir = Path(__file__).parent
csv_path = current_dir.parent / 'data' / 'art_metadata_embedding.csv'
df = pd.read_csv(csv_path)

user_data_path = current_dir.parent / 'data' / 'user_data.csv'


app = FastAPI()

@app.get("/questions", response_model=allProfileQuestionModel)
async def get_questions():
    """
    Fetch a list of questions for the user profiling.
    A list of images in the following format:
    
        question_id: int
            image_id: int
            image_title: str

    """
    allQuestions = create_all_profile_questions()
    return allQuestions

@app.post("/responses")
async def store_responses(user_responses: allProfileResponseModel):
    """
    Store user responses for the questionnaire.
    """

    def get_response_choice_ids(responses: allProfileResponseModel):
        return [response.choice_image_id for response in responses.responses]

    id_list = get_response_choice_ids(user_responses)

    # Find rows corresponding to the selected IDs
    selected_rows = df[df['ID'].isin(id_list)]

    # Assuming embeddings are stored as 'emb_0' to 'emb_1023'
    embedding_columns = [f'emb_{i}' for i in range(1024)]
    mean_embedding = selected_rows[embedding_columns].mean()

    # Store the mean embedding in the user's profile
    user_name = user_responses.user_name or "guest_login"
    user_data = pd.read_csv(user_data_path)

    if user_name in user_data['username'].values:
        user_data.loc[user_data['username'] == user_name, embedding_columns] = mean_embedding.values
    else:
        new_user_row = pd.DataFrame([[user_name] + [10] + mean_embedding.tolist()], columns=['username', 'viewed'] + embedding_columns)
        user_data = pd.concat([user_data, new_user_row], ignore_index=True)


    user_data.to_csv(user_data_path, index=False)

    return {"message": f"User responses stored successfully for {user_name}."}


# Test Function
@app.get("/test")
def test():
    return {"message": "Hello World"}


@app.get("/create_embeddings")
def create_embeddings():
    process_dataframe(df)
    return {"message": "Embeddings Generated"}

@app.get("/create_index")
def create_index():
    create_faiss_index(df)
    return {"message": "Index Created"}


@app.get("/get_recommendation_random", response_model=List[dict])
async def get_recommendation_random(n: int = 15):
    """
    Returns N randomly selected images from the CSV file.
    Each image has a nested JSON with 'FILE', 'TITLE', and 'AUTHOR'.
    """

    if n <= 0:
        raise HTTPException(status_code=400, detail="Number of recommendations must be positive")

    # Check if the DataFrame has enough rows
    if n > len(df):
        raise HTTPException(status_code=400, detail=f"Cannot provide {n} recommendations. Only {len(df)} available.")

    # Randomly select N rows from the DataFrame
    recommendations = df.sample(n).to_dict(orient='records')

    # Formatting the response
    formatted_response = []
    for idx, rec in enumerate(recommendations, 1):
        formatted_response.append({
            "recommendation": idx,
            "details": {
                "FILE": rec.get("FILE", ""),
                "TITLE": rec.get("TITLE", ""),
                "AUTHOR": rec.get("AUTHOR", "")
            }
        })

    return formatted_response


@app.get("/get_recommendation_by_profile", response_model=List[dict])
async def get_recommendation_by_profile(user_name: str, n: int = 15):
    """
    Returns recommendations based on the user's viewing history.
    Each recommended item has a nested JSON with 'FILE', 'TITLE', and 'AUTHOR'.
    """

    data_folder = Path(os.getcwd()).parent / "data" 

    user_df = pd.read_csv(data_folder/"user_data.csv")  # assuming user data is in 'user_data.csv'
    embeddings_df = pd.read_csv(data_folder/"art_metadata_embedding.csv")  # assuming embeddings are in 'embeddings.csv'

    # Retrieve user embedding
    if user_name not in user_df['username'].values:
        raise HTTPException(status_code=404, detail=f"User '{user_name}' not found")

    user_data = user_df[user_df['username'] == user_name].iloc[0]
    user_embedding = np.array([user_data[f'emb_{i}'] for i in range(1024)], dtype=float)
    
    # Retrieve similar items using FAISS
    faiss_index = faiss.read_index("embedding_model/faiss_index.pickle")
    similar_indices = retrieve_similar_items(user_embedding, faiss_index, n)
    similar_rows = get_dataframe_rows(embeddings_df, similar_indices)

    # Formatting the response
    formatted_response = []
    for idx, rec in enumerate(similar_rows.to_dict(orient='records'), 1):
        formatted_response.append({
            "recommendation": idx,
            "details": {
                "FILE": rec.get("FILE", ""),
                "TITLE": rec.get("TITLE", ""),
                "AUTHOR": rec.get("AUTHOR", "")
            }
        })

    return formatted_response


@app.get("/get_recommendation_by_prompt", response_model=List[dict])
async def get_recommendation_by_prompt(prompt: str, n: int = 15):
    """
    Returns recommendations based on the user's viewing history.
    Each recommended item has a nested JSON with 'FILE', 'TITLE', and 'AUTHOR'.
    """

    # Load user data and embeddings DataFrame
    data_folder = Path(os.getcwd()).parent / "data" 

    embeddings_df = pd.read_csv(data_folder/"art_metadata_embedding.csv")  # assuming embeddings are in 'embeddings.csv'

    prompt_embedding = get_bert_embedding(prompt)

    # Retrieve similar items using FAISS
    faiss_index = faiss.read_index("embedding_model/faiss_index.pickle")
    similar_indices = retrieve_similar_items(prompt_embedding, faiss_index, n)
    similar_rows = get_dataframe_rows(embeddings_df, similar_indices)

    # Formatting the response
    formatted_response = []
    for idx, rec in enumerate(similar_rows.to_dict(orient='records'), 1):
        formatted_response.append({
            "recommendation": idx,
            "details": {
                "FILE": rec.get("FILE", ""),
                "TITLE": rec.get("TITLE", ""),
                "AUTHOR": rec.get("AUTHOR", "")
            }
        })

    return formatted_response


def retrieve_similar_items(embedding, faiss_index, top_k=5):
    # Function to retrieve similar items
    distances, indices = faiss_index.search(np.array([embedding]), top_k)
    return indices[0]

def get_dataframe_rows(df, indices):
    # Function to get actual rows from DataFrame based on indices
    return df.iloc[indices]

