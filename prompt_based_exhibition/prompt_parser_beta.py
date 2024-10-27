import openai
from pydantic import BaseModel
import os

import dotenv
dotenv.load_dotenv()

# Define the schema using Pydantic
class ArtInfo(BaseModel):
    tags: list[str]
    artists: list[str]

class EntityParser:
    def __init__(self, model='gpt-4o-mini', api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model

    def extract_entities(self, user_input):
        system_prompt = """You are an expert in art and artists. Your task is to identify artwork tags (like style, genre, etc.) and artist names from user input and return them in a structured format: tags and artists.

        Return only the tags and artists explicitly mentioned. Do not infer or add any additional tags or artists that weren't directly stated.

        When identifying artists, always return their full names if possible. For example, if the user mentions "Vincent", return "Vincent van Gogh".

        Return empty lists for both tags and artists if no specific tags or artists are mentioned.

        Examples:
        1. Input: "I like colorful paintings"
           Output: {"tags": ['colorful'], "artists": []}
        2. Input: "I love the works of Vincent"
           Output: {"tags": [], "artists": ["Vincent van Gogh"]}
        3. Input: "I'm a fan of Impressionism and Cubism"
           Output: {"tags": ["Impressionism", "Cubism"], "artists": []}
        4. Input: "I like Monet's water lilies"
           Output: {"tags": ["water lilies"], "artists": ["Claude Monet"]}
        5. Input: "I like old age artworks"
           Output: {"tags": ["old age"], "artists": []}
        6. Input: "I enjoy modern art"
           Output: {"tags": ["modern art"], "artists": []}"""

        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                response_format=ArtInfo,
            )
            art_info = completion.choices[0].message.parsed
            return art_info.tags, art_info.artists
        except Exception as e:
            print(f"Error in extracting entities: {e}")
            return [], []

if __name__ == "__main__":
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    api_key = os.getenv("OPENAI_API_KEY")
    bot = EntityParser(model="gpt-4o-mini", api_key=api_key)
    
    # Example usage
    # user_input = "I love the works of vincent van gogh, especially his Renaissance and Realism paintings."
    user_input = "I like colorful artwork"
    tags, artists = bot.extract_entities(user_input)
    print("Tags:", tags)
    print("Artists:", artists)
