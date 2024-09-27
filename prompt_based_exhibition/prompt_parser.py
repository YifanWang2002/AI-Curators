import openai
from pydantic import BaseModel
import os
from time import time

class ArtInfo(BaseModel):
    tags: list[str]
    artists: list[str]

class OpenAIChatbot:
    def __init__(self, model='gpt-4', api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model

    def paraphrase2(self, user_input):
        system_prompt = """You are an expert in artworks and artists. Your task is to paraphrase and summarize the user input to identify their taste of arts. The users may input one or few sentences, and you will summarize them into one comprehensive sentence that contains only keywords relevant to arts and remove irrelevant stop words.

        You can paraphrase and thus modify the user input to make it more concise and clear. For example, if the user input is "I like paintings with bright colors and bold brush strokes", you can paraphrase it as "colorful and expressive paintings".

        When user input is incomplete, you can infer the missing information based on the context. For example, if the user input is "I like Monet's water lilies", you can infer that the user likes paintings by Claude Monet.

        Examples:
        1. Input: "I like colorful paintings"
           Output: "colorful paintings"
        2. Input: "I love the works of Vincent"
           Output: "Artworks of Vincent Van Gogh"
        3. Input: "I want to see people celebrating cultural festivals or traditions"
           Output: "people celebrating cultural festivals or traditions"
        4. Input: "I like Monet's water lilies"
           Output: "Claude Monet's water lilies and paintings"
        5. Input: "I like paintings of people"
           Output: "Portraits and figurative paintings of one or more people"
        """

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                temperature=0,
                max_tokens=512,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error in extracting entities: {e}")
            return []  # Return empty list in case of an error

    def paraphrase(self, user_input):
        system_prompt = """
        You are an expert in artworks and artists. When someone inputs one or a few sentences, your task is to extract key information from it. The key information should include the artist(s) mentioned, the tag(s) mentioned, and a concise summary of the original input. When the input is very clear, you should only extract information from the input without making any additional assumptions. When the input is vague or incomplete, you can infer based on the context in order to extract enough information. When there are errors in input (such as typos or incomplete typing), you can fix the errors.
        For a given input, your answer should structure as follows:
        “artists: <list> a list of artists that the input mentions; tags: <list> a paragraph that introduces the themed exhibition to viewers; summary: <string> a concise and clear summary that paraphrases and summarizes the original input”
        Examples:
        1. Input: "I like colorful paintings"
           Output: "tags: Fauvism, Pop Art, Abstract Expressionism; artists: []; summary: colorful paintings "
        2. Input: "I love the works of Vincent"
           Output: " tags: []; artists: Vincent Van Gogh; summary: Artworks of Vincent Van Gogh"
        3. Input: "I like Monet's water lilies"
           Output: " tags: scenery, figure, landscape, impressionism; artists: Claude Monet; summary: Claude Monet's water lilies and paintings"
        """
        # 3. Input: "I want to see people celebrating cultural festivals or traditions"
        #    Output: "people celebrating cultural festivals or traditions"
        # 4. Input: "I like Monet's water lilies"
        #    Output: "Claude Monet's water lilies and paintings"
        # 5. Input: "I like paintings of people"
        #    Output: "Portraits and figurative paintings of one or more people"

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                temperature=0,
                max_tokens=512,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            # return completion.choices[0].message.content
        except Exception as e:
            print(f"Error in extracting entities: {e}")
            return [], []  # Return empty lists in case of an error
        temp = completion.choices[0].message.content.split('; ')
        temp = [str(x).strip() for x in temp]
        temp2 = {}
        for i in range(len(temp)):
            if 'artists:' in temp[i]:
                arists = temp[i].replace('artists:', '').strip()
                if '[]' in arists:
                    temp2['artists'] = []
                else:
                    temp2['artists'] = arists.split(', ')
            elif 'tags:' in temp[i]:
                tags = temp[i].replace('tags:', '').strip()
                if '[]' in tags:
                    temp2['tags'] = []
                else:
                    temp2['tags'] = tags.split(', ')
            else:
                temp2['summary'] = temp[i].replace('summary:', '').strip()
        return completion.choices[0].message.content, temp2
        
    def extract_entities(self, user_input):
        system_prompt = """You are an expert in art and artists. Your task is to identify potential preference of artists and artwork tags (styles, themes, movements, genres, objects, etc.) from user input and return them in a structured format: tags and artists.

        If the user input is specific, return only the tags and artists explicitly mentioned. Do not infer or add any additional styles or artists that weren't directly stated or strongly implied.

        If the user input is vague or open-ended (e.g., "I like old age artworks"), use your knowledge to infer potential tags that might fit the description. For example, "old age artworks" could refer to Renaissance, Baroque, Medieval, or Rococo styles.

        When identifying artists, always return their full names if possible. For example, if the user mentions "Vincent", return "Vincent van Gogh".

        Only return empty lists for both tags and artists if the input is extremely vague (e.g. "I love art.") or unrelated to art (e.g. "How are you today").

        Examples:
        1. Input: "I like colorful paintings"
           Output: {"tags": ["Fauvism", "Pop Art", "Abstract Expressionism"], "artists": []}
        2. Input: "I love the works of Vincent"
           Output: {"tags": [], "artists": ["Vincent van Gogh"]}
        3. Input: "I'm a fan of Impressionism and Cubism"
           Output: {"tags": ["Impressionism", "Cubism"], "artists": []}
        4. Input: "I like Monet's water lilies"
           Output: {"tags": [plant, water lilies], "artists": ["Claude Monet"]}
        5. Input: "I like paintings of people"
           Output: {"tags": ["Portrat", "People", "Figurative"], "artists": []}
        6. Input: "I enjoy modern art"
           Output: {"tags": ["Abstract Expressionism", "Pop Art", "Minimalism", "Surrealism"], "artists": []}"""

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
            return art_info.tags, art_info.artists
        except Exception as e:
            print(f"Error in extracting entities: {e}")
            return [], []  # Return empty lists in case of an error
    
    def parse(self, user_input):
        tag_begin = time()
        tags, artists = self.extract_entities(user_input)
        print(f"***Tag extraction time: {time() - tag_begin}")
        parse_begin = time()
        parsed_promt = self.paraphrase2(user_input)
        print(f"***Parse time: {time() - parse_begin}")
        return tags, artists, parsed_promt

