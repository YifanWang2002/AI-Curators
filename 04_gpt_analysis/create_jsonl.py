import json
import base64
import pandas as pd
from openai import OpenAI

# Please store the api key in your environment variables
client = OpenAI()

# Function to encode image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
    

# Fill in the corresponding path to the csv 
df = pd.read_csv('path_to_cleaned_data.csv')


system_prompt = """
You are an art professionalist tasked with analyzing artworks and providing detailed, insightful descriptions. For each given artwork image and metadata, generate a JSON object containing the following keys and values:

intro: (string, max 15 words) An elegant description of the artwork **without referencing any metadata.** 
overview: (string, max 100 words) A detailed description of what is depicted in the artwork.
style: (string, max 150 words) Analyze and describe the artwork's style. Consider brushstrokes, color palettes, composition, and other visual elements.  Explain how these elements contribute to the overall aesthetic.
style_tags: (list of strings) List specific art style keywords applicable to the artwork.
theme: (string, max 100 words) Interpret and describe the artwork's underlying theme or message. 
theme_tags: (list of strings) List keywords related to the identified theme(s).
main_objects: (JSON object)  Identify the most prominent objects in the artwork. Use object names as keys and provide a 30-word description of each object's appearance and role within the artwork's context as values.
other_objects: (list of strings) List any remaining identifiable objects present in the artwork not included in "main_objects."
movements: (list of strings) List art movements the artwork clearly belongs to or is significantly influenced by. 

"""

jsonl_content = []

# OpenAI API has a limit of 135,000 tokens per request, so we will split the data into chunks
df_2000 = df[1000:2000]

for i, row in df_2000.iterrows():
    url = row['azure_image_url']
    meta_str = f"Title: {row['title']}. Artist: {row['display_name']}."
    jsonl_content.append({
        "custom_id": f"request-{row['artwork_id']}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "gpt-4o",
            "response_format": { "type": "json_object" },
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": meta_str
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": url
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }
    })


with open('batchinput_artwork_2000.jsonl', 'w') as f:
    for entry in jsonl_content:
        json.dump(entry, f)
        f.write('\n')
