import os
import shutil
import torch
import open_clip
import faiss

import pandas as pd
import numpy as np

from sentence_transformers import SentenceTransformer
from PIL import Image

from io import BytesIO
import requests
import prompt_parser
from exhibition_curator import ExhibitionCurator
import json
from sklearn.metrics.pairwise import cosine_similarity
from time import time


DATA_DIR = r"D:\Metaverse_Museum\AI-Curators\data"
OUTPUT_DIR = r"D:\Metaverse_Museum\AI-Curators\prompt_based_exhibition\output"
Image.MAX_IMAGE_PIXELS = 933120000
# Create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# a function to convert string of list to actual list
def string_to_list(string):
    string = string.replace("[", "")
    string = string.replace("]", "")
    string = string.replace("'", "")
    string = string.split(", ")
    return string

class Prompt_exhibition_generator:
    def __init__(self, model_e5='intfloat/e5-large-v2', model_clip='ViT-SO400M-14-SigLIP-384', api_key=None, mode = 'tag'):
        e5_index_path = os.path.join(DATA_DIR, f"artworks_e5.index")
        # ======================  Create Index  ====================== #
        # e5_embeddings = np.load(os.path.join(DATA_DIR, "search_embeds_e5_v2.npy"))
        # print(e5_embeddings.shape)
        # e5_index = create_faiss_index(e5_embeddings, e5_index_path)

        self.e5_index = faiss.read_index(e5_index_path)

        clip_index_path = os.path.join(DATA_DIR, f"artworks_clip.index")
        # ======================  Create Index  ====================== #
        # clip_embeddings = np.load(os.path.join(DATA_DIR, "search_embeds_clip_v2.npy"))
        # print(clip_embeddings.shape)
        # clip_index = create_faiss_index(clip_embeddings, clip_index_path)

        self.clip_index = faiss.read_index(clip_index_path)

        self.metadata = pd.read_csv(os.path.join(DATA_DIR, "tags_replaced.csv"))
        print(self.metadata.shape)

        self.metadata['tags'] = self.metadata['tags'].apply(string_to_list)
        self.tag_model = SentenceTransformer('all-MiniLM-L6-v2')

        self.e5_model = SentenceTransformer("intfloat/e5-large-v2")

        self.clip_model, _, _ = open_clip.create_model_and_transforms(
            "ViT-SO400M-14-SigLIP-384", pretrained="webli"
        )
        self.clip_tokenizer = open_clip.get_tokenizer("ViT-SO400M-14-SigLIP-384")
        self.parser = prompt_parser.OpenAIChatbot(model="gpt-4o-mini", api_key='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')
    
    def get_tag_embeddings(self, row):
        embeddings = []
        for tag in row['tags']:
            embeddings.append(self.tag_model.encode(tag))
        return embeddings
    
    def get_artist_embeddings(self, row):
        return self.tag_model.encode(str(row['display_name']))
    
    def search_tags_and_artists(self, row, tags, artists):
        if len(tags) == 0 and len(artists) == 0:
            return True
        search_result = 0
        for tag in tags:
            temp_embedding = self.tag_model.encode(tag)
            for tag_embedding in row['tag_embeddings']:
                # use cosine similarity to compare the embeddings
                if cosine_similarity([temp_embedding], [tag_embedding])[0][0] >= 0.3:
                    search_result += 1
                    break
        for artist in artists:
            temp_embedding = self.tag_model.encode(artist)
            # use cosine similarity to compare the embeddings
            if cosine_similarity([temp_embedding], [row['artist_embedding']])[0][0] >= 0.8:
                search_result += 1
                break
        return search_result == len(tags) + len(artists)
    
    def filter_search_results(self, tags, artists, results):
        results['tag_embeddings'] = results.apply(self.get_tag_embeddings, axis=1)
        results['artist_embedding'] = results.apply(self.get_artist_embeddings, axis=1)
        results = results[results.apply(self.search_tags_and_artists, args=(tags, artists), axis=1)]
        return results

    def create_faiss_index(self, embeddings, index_path):
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, index_path)

        return index
        
    def e5_search(self, query, model, index, k):
        query_embedding = model.encode(query, normalize_embeddings=True)
        D, I = index.search(query_embedding[None, :], k)
        return D, I


    def clip_search(self, query, tokenizer, model, index, k):
        query = tokenizer(query)
        query_embedding = model.encode_text(query).numpy()
        query_embedding /= np.linalg.norm(query_embedding, axis=1, keepdims=True)
        D, I = index.search(query_embedding, k)
        return D, I


    def save_images(self, filepath, image_ids, nrow=5):
        # check if the data type of image_ids is a pandas series
        # if isinstance(image_ids, pd.Series):
        #     images = [Image.open(f"../GPT/images/{image_id}.jpg") for image_id in image_ids]
        # else:
        images = []
        temp_df = self.metadata[self.metadata["artwork_id"].isin(image_ids)]
        for url in temp_df["compressed_url"]:
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            images.append(img)

        # Calculate the size of the grid
        nrows = (len(images) + nrow - 1) // nrow  # Calculate required number of rows
        max_widths = [0] * nrow
        max_heights = [0] * nrows
        for i, img in enumerate(images):
            row, col = divmod(i, nrow)
            max_widths[col] = max(max_widths[col], img.width)
            max_heights[row] = max(max_heights[row], img.height)

        total_width = sum(max_widths)
        total_height = sum(max_heights)

        # Create a new blank image for the grid
        grid_image = Image.new("RGB", (total_width, total_height))

        # Paste images into the grid
        y_offset = 0
        for row in range(nrows):
            x_offset = 0
            for col in range(nrow):
                if row * nrow + col < len(images):
                    grid_image.paste(images[row * nrow + col], (x_offset, y_offset))
                x_offset += max_widths[col]
            y_offset += max_heights[row]

        grid_image.save(filepath)
        print(f"Image saved as {filepath}")

    def parse_prompt(self, prompt, parser_mode = None):
        if parser_mode == None:
            parser_mode = self.mode
        if parser_mode == 'old':
            # call a GPT agent to parse the prompt
            # @TODO: also inference if need to do exact match or to infer for more paintings...
            # @TODO: ? Looking for specific results OR ? open-ended search
            parsed_promt = self.parser.paraphrase2(prompt)
            return parsed_promt
        else:
            # call a GPT agent to parse the prompt
            tags, artists, parsed_promt = self.parser.parse(prompt)
            return tags, artists, parsed_promt
        
    def query_search(self, query):
        with torch.no_grad(), torch.amp.autocast('cuda'):
            D, I = self.e5_search("query: " + query, self.e5_model, self.e5_index, 500)
            e5_result = pd.DataFrame({"score": D[0]}, index=I[0])

            D, I = self.clip_search(query, self.clip_tokenizer, self.clip_model, self.clip_index, 500)
            clip_result = pd.DataFrame({"score": D[0]}, index=I[0])

            result = e5_result.join(
                clip_result, how="inner", lsuffix="_e5", rsuffix="_clip"
            )
            result["score"] = result["score_e5"] + result["score_clip"]
            result = result.join(self.metadata, how="inner")
            result.sort_values(by="score", ascending=False, inplace=True)
            # result.to_csv(os.path.join(OUTPUT_DIR, filename + ".csv"))
            # if "artwork_id" in result.columns:
            #     save_images(
            #         os.path.join(OUTPUT_DIR, filename + ".jpg"),
            #         result[["artwork_id", "compressed_url"]].head(25),
            #     )
            # else:
            #     save_images(
            #         os.path.join(OUTPUT_DIR, filename + ".jpg"),
            #         result["image_id"].head(25),
            #     )
        return result
    def tag_search(self, parsed_prompt):
        raise NotImplementedError # To be implemented in the future
        pass

    def search(self, prompt, search_mode = None):
        if search_mode == None:
            search_mode = self.mode
        parse_begin = time()
        tags, artists, parsed_prompt = self.parse_prompt(prompt, parser_mode=search_mode)
        print(f"***Total time taken to parse the prompt: {time() - parse_begin} seconds")
        search_begin = time()
        if search_mode == 'old':
            results = self.query_search(parsed_prompt)
        else:
            results = self.query_search(parsed_prompt)
        print(f"***Total time taken to search: {time() - search_begin} seconds")
        return tags, artists, results
    
    def generate_exhibition(self, prompt, search_mode='phrase'):
        begin = time()
        # results = self.search(prompt)
        # curator = ExhibitionCurator(api_key="sk-proj-tKerDbMKo81VQLdiGM1fT3BlbkFJuUOpUNnT9EVIv8vZtorg", metadata=self.metadata)
        # exhibitions = curator.curate(results)
        # return exhibitions
        if not os.path.exists(OUTPUT_DIR+'\\'+prompt):
            os.makedirs(OUTPUT_DIR+'\\'+prompt)
        tags, artists, result = self.search(prompt, search_mode)
        # @TODO: filter results based on tags and artists
        filter_begin = time()
        filtered_result = self.filter_search_results(tags, artists, result)
        print(f"***Total time taken to filter the results: {time() - filter_begin} seconds")
        if len(filtered_result) == 0:
            print("No results found for the given tags and artists")
        elif len(filtered_result) < len(result):
            print("Successfully filtered the results based on tags and artists")
        result = filtered_result.iloc[:60]
        curate_begin = time()
        curator = ExhibitionCurator(api_key="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", metadata=self.metadata)
        exhibitions = curator.curate(result, query=prompt)
        print(f"***Total time taken to curate the exhibitions: {time() - curate_begin} seconds")
        for i, exhibition in enumerate(exhibitions):
            with open(os.path.join(OUTPUT_DIR+'\\'+prompt, f'Exhibition_{i}' + ".json"), 'w') as f:
                json.dump(exhibition, f, indent=4)
            f.close()
            self.save_images(os.path.join(OUTPUT_DIR+'\\'+prompt, f'Exhibition_{i}' + ".jpg"), exhibition['art_pieces'])
        print(f"***Total time taken to generate the exhibition: {time() - begin} seconds")

if __name__ == "__main__":
    agent = Prompt_exhibition_generator()
    prompts = [
            "I want to see loneliness and depression",
            "I want to see paintings showcase youth and energy",
            "I like flowers",
            "I love simple paintings"
            # "women in blue clothes",
            # "Gothic architecture",
            # "sport activities",
            # "crowd on a beach or a riverbank",
            # "Painting of joy",
            # "Vincent van Gogh",
            # "Vincent Vangogh",
            # "people celebrating cultural festivals or traditions",
            # "paintings showing agricultural life",
            # "Vincent van Gogh",
            # "pictures with large areas of red",
            # "colorful spring",
            # "bold color",
            # "pictures containing christian cross",
            # "Portraits of historical figures in the Renaissance era",
            # "warm, cozy feeling of autumn",
            # "cute cats",
            # "women with apple",
            # "apple still life",
            # "16th century",
            # "Polish Art",
            # "Artist portraits",
            # "loneliness and depression",
            # "paintings showcase youth and energy",
            # "Floral",
            # "Vase",
            # "Impressionism",
            # "Loose brushwork",
            # "Baroque Era",
        ]
    while True:
        prompt = input("Prompt to search: ")
        if prompt.lower() in ['exit', 'quit', 'bye']:
            print("Goodbye!")
            break

        if not os.path.exists(OUTPUT_DIR+'\\'+prompt):
            os.makedirs(OUTPUT_DIR+'\\'+prompt)
        result = agent.search(prompt, search_mode='phrase')
        result = result.iloc[:50]
        # filename = prompt.replace(" ", "_")
        # results.to_csv(os.path.join(OUTPUT_DIR, filename + ".csv"))
        # if "artwork_id" in results.columns:
        #     agent.save_images(
        #         os.path.join(OUTPUT_DIR, filename + ".jpg"),
        #         results[["artwork_id", "compressed_url"]].head(25),
        #     )
        # else:
        #     agent.save_images(
        #         os.path.join(OUTPUT_DIR, filename + ".jpg"),
        #         results["image_id"].head(25),
        #     )
        curator = ExhibitionCurator(api_key="sk-proj-tKerDbMKo81VQLdiGM1fT3BlbkFJuUOpUNnT9EVIv8vZtorg", metadata=agent.metadata)
        exhibitions = curator.curate(result)
        for i, exhibition in enumerate(exhibitions):
            with open(os.path.join(OUTPUT_DIR+'\\'+prompt, f'Exhibition_{i}' + ".json"), 'w') as f:
                json.dump(exhibition, f, indent=4)
            f.close()
            agent.save_images(os.path.join(OUTPUT_DIR+'\\'+prompt, f'Exhibition_{i}' + ".jpg"), exhibition['art_pieces'])