import os
import openai
import pandas as pd


# Initialize OpenAI client
client = openai.OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url="https://cmu.litellm.ai",
)


# Function to get description for each location
def get_movement_description(movement):
    prompt = f"Create an elegant 80-word description that captures the essence of the given art genre, highlighting its key features and historical evolution. Genre: {movement}"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content
    return content


df = pd.DataFrame({"movement": ["Nature", "Sacred"]})
# Apply the function to each location and create a new column
df["description"] = df["movement"].apply(get_movement_description)

df.to_csv("data/movement_description.csv", index=False)
