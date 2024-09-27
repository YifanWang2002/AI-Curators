import os
import openai
import pandas as pd


# Initialize OpenAI client
client = openai.OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url="https://cmu.litellm.ai",
)


# Function to get description for each location
def get_location_description(location):
    prompt = f"Create an elegant 80-word historical overview tracing the evolution of artworks at the specified location. Location: {location}"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content
    return content


df = pd.DataFrame({"location": ["New York", "Byzantine Empire"]})
# Apply the function to each location and create a new column
df["description"] = df["location"].apply(get_location_description)

df.to_csv("data/location_description.csv", index=False)
