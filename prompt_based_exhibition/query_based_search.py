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


DATA_DIR = ".\\data"
OUTPUT_DIR = ".\\prompt_based_exhibition\\output"
Image.MAX_IMAGE_PIXELS = 933120000
# Create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

class prompt_exhibition_generator:
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

        self.e5_model = SentenceTransformer("intfloat/e5-large-v2")

        self.clip_model, _, _ = open_clip.create_model_and_transforms(
            "ViT-SO400M-14-SigLIP-384", pretrained="webli"
        )
        self.clip_tokenizer = open_clip.get_tokenizer("ViT-SO400M-14-SigLIP-384")
        self.parser = prompt_parser.OpenAIChatbot(model="gpt-4o-mini", api_key='sk-proj-tKerDbMKo81VQLdiGM1fT3BlbkFJuUOpUNnT9EVIv8vZtorg')
    
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
        if parser_mode == 'tag':
            # call a GPT agent to parse the prompt
            # @TODO: also inference if need to do exact match or to infer for more paintings...
            # @TODO: ? Looking for specific results OR ? open-ended search
            tags, artists = self.parser.extract_entities(prompt)
            return([tags, artists])
        else:
            # call a GPT agent to parse the prompt
            parsed_promt = self.parser.paraphrase(prompt)
            return parsed_promt
        
    def query_search(self, query):
        with torch.no_grad(), torch.cuda.amp.autocast():
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
        parsed_prompt = self.parse_prompt(prompt, parser_mode=search_mode)
        if search_mode == 'tag':
            results = self.tag_search(parsed_prompt)
        else:
            results = self.query_search(parsed_prompt)
        return results

if __name__ == "__main__":
    agent = prompt_exhibition_generator()
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