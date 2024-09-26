import openai
from pydantic import BaseModel
import os
from ArtSearch import ArtSearch

# Define the schema using Pydantic
class ArtInfo(BaseModel):
    styles: list[str]
    artists: list[str]

class OpenAIChatbot:
    def __init__(self, model='gpt-4o-mini', api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model

    def extract_entities(self, user_input):
        system_prompt = """You are an expert in art and artists. Your task is to identify art styles and artist names from user input and return them in a structured format: styles and artists.

        If the user input is specific, return only the styles and artists explicitly mentioned. Do not infer or add any additional styles or artists that weren't directly stated or strongly implied.

        If the user input is vague or open-ended (e.g., "I like old age artworks"), use your knowledge to infer potential styles that might fit the description. For example, "old age artworks" could refer to Renaissance, Baroque, Medieval, or Rococo styles.

        When identifying artists, always return their full names if possible. For example, if the user mentions "Vincent", return "Vincent van Gogh".

        Only return empty lists for both styles and artists if the input is extremely vague or unrelated to art.

        Examples:
        1. Input: "I like colorful paintings"
           Output: {"styles": ["Fauvism", "Pop Art", "Abstract Expressionism"], "artists": []}
        2. Input: "I love the works of Vincent"
           Output: {"styles": [], "artists": ["Vincent van Gogh"]}
        3. Input: "I'm a fan of Impressionism and Cubism"
           Output: {"styles": ["Impressionism", "Cubism"], "artists": []}
        4. Input: "I like Monet's water lilies"
           Output: {"styles": [], "artists": ["Claude Monet"]}
        5. Input: "I like old age artworks"
           Output: {"styles": ["Renaissance", "Baroque", "Medieval", "Rococo"], "artists": []}
        6. Input: "I enjoy modern art"
           Output: {"styles": ["Abstract Expressionism", "Pop Art", "Minimalism", "Surrealism"], "artists": []}"""

        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                response_format=ArtInfo,  # Define the response format
            )
            art_info = completion.choices[0].message.parsed
            return art_info.styles, art_info.artists
        except Exception as e:
            print(f"Error in extracting entities: {e}")
            return [], []  # Return empty lists in case of an error

class UserProfile:
    def __init__(self, user_id):
        self.user_id = user_id
        self.tags = set()      # duplicate entries
        self.artists = set()

    def update_profile(self, new_tags, new_artists):
        self.tags.update(new_tags)
        self.artists.update(new_artists)

    def get_profile(self):
        return {
            "tags": list(self.tags),
            "artists": list(self.artists)
        }


def chat_interface(user_profile, bot, art_search):
    print("Welcome to the art recommendation system! Tell me about your preferences.")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("Thank you for using the art recommendation system. Goodbye!")
            break

        if user_input.lower() == 'clean':
            user_profile = UserProfile(user_id="justin")
            print("Profile reset. Let's start again!")
            continue
        
        tags, artists = bot.extract_entities(user_input)
        
        user_profile.update_profile(tags, artists)
        
        print("Updated Profile:")
        print("Tags:", user_profile.get_profile()['tags'])
        print("Artists:", user_profile.get_profile()['artists'])
        
        # Perform search based on updated profile
        if user_profile.get_profile()['artists']:
            print("\nRecommended artists based on your preferences:")
            for artist in user_profile.get_profile()['artists']:
                results = art_search.search(artist, search_type='name')
                print(f"Similar to {artist}:")
                for i, (result, score) in enumerate(results[:5], 1):
                    print(f"  {i}. {result} (Score: {score:.4f})")

        if user_profile.get_profile()['tags']:
            print("\nRecommended tags based on your preferences:")
            for tag in user_profile.get_profile()['tags']:
                results = art_search.search(tag, search_type='tag')
                print(f"Similar to {tag}:")
                for i, (result, score) in enumerate(results[:5], 1):
                    print(f"  {i}. {result} (Score: {score:.4f})")

        
if __name__ == "__main__":
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    api_key = os.getenv("OPENAI_API_KEY")
    bot = OpenAIChatbot(model="gpt-4o-mini", api_key=api_key)
    art_search = ArtSearch()
    user_profile = UserProfile(user_id="justin")
    chat_interface(user_profile, bot, art_search)

    # test cases
    # "I love the works of vincent van gogh, especially his Renaissance and Realism paintings."
    # The dramatic style of the Baroque period, especially Caravaggio's religious scenes, really resonates with me.
    # I'm a big fan of the Impressionist movement, particularly Claude Monet's landscapes.
    # I really appreciate the bold colors and forms in the works of Jackson Pollock and other Abstract Expressionists.
    # Gothic art and architecture, with its intricate details and soaring structures, are truly mesmerizing to me.