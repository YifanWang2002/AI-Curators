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

DATA_DIR = r"../data"
OUTPUT_DIR = r"output"
Image.MAX_IMAGE_PIXELS = 933120000

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def string_to_list(string):
    return string.replace("[", "").replace("]", "").replace("'", "").split(", ")

class Prompt_exhibition_generator:
    def __init__(self, model_e5='intfloat/e5-large-v2', model_clip='ViT-SO400M-14-SigLIP-384', api_key=None, mode='tag'):
        e5_index_path = os.path.join(DATA_DIR, "artworks_e5.index")
        self.e5_index = faiss.read_index(e5_index_path)
        clip_index_path = os.path.join(DATA_DIR, "artworks_clip.index")
        self.clip_index = faiss.read_index(clip_index_path)
        self.metadata = pd.read_csv(os.path.join(DATA_DIR, "tags_replaced.csv"))
        self.metadata['tags'] = self.metadata['tags'].apply(string_to_list)
        self.tag_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.e5_model = SentenceTransformer("intfloat/e5-large-v2")
        self.clip_model, _, _ = open_clip.create_model_and_transforms("ViT-SO400M-14-SigLIP-384", pretrained="webli")
        self.clip_tokenizer = open_clip.get_tokenizer("ViT-SO400M-14-SigLIP-384")
        self.parser = prompt_parser.OpenAIChatbot(model="gpt-4o-mini", api_key='your key')
    
    def get_tag_embeddings(self, row):
        return [self.tag_model.encode(tag) for tag in row['tags']]
    
    def get_artist_embeddings(self, row):
        return self.tag_model.encode(str(row['display_name']))
    
    def search_tags_and_artists(self, row, tags, artists):
        if not tags and not artists:
            return True
        search_result = 0
        for tag in tags:
            temp_embedding = self.tag_model.encode(tag)
            if any(cosine_similarity([temp_embedding], [te])[0][0] >= 0.3 for te in row['tag_embeddings']):
                search_result += 1
        for artist in artists:
            temp_embedding = self.tag_model.encode(artist)
            if cosine_similarity([temp_embedding], [row['artist_embedding']])[0][0] >= 0.8:
                search_result += 1
        return search_result == len(tags) + len(artists)
    
    def filter_search_results(self, tags, artists, results):
        results['tag_embeddings'] = results.apply(self.get_tag_embeddings, axis=1)
        results['artist_embedding'] = results.apply(self.get_artist_embeddings, axis=1)
        return results[results.apply(self.search_tags_and_artists, args=(tags, artists), axis=1)]
    
    def create_faiss_index(self, embeddings, index_path):
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, index_path)
        return index
    
    def e5_search(self, query, model, index, k):
        query_embedding = model.encode(query, normalize_embeddings=True)
        return index.search(query_embedding[None, :], k)
    
    def clip_search(self, query, tokenizer, model, index, k):
        query_embedding = model.encode_text(tokenizer(query)).numpy()
        query_embedding /= np.linalg.norm(query_embedding, axis=1, keepdims=True)
        return index.search(query_embedding, k)
    
    def save_images(self, filepath, image_ids, nrow=5):
        images = []
        temp_df = self.metadata[self.metadata["artwork_id"].isin(image_ids)]
        for url in temp_df["compressed_url"]:
            response = requests.get(url)
            images.append(Image.open(BytesIO(response.content)))
        nrows = (len(images) + nrow - 1) // nrow
        max_widths = [0] * nrow
        max_heights = [0] * nrows
        for i, img in enumerate(images):
            row, col = divmod(i, nrow)
            max_widths[col] = max(max_widths[col], img.width)
            max_heights[row] = max(max_heights[row], img.height)
        total_width = sum(max_widths)
        total_height = sum(max_heights)
        grid_image = Image.new("RGB", (total_width, total_height))
        y_offset = 0
        for row in range(nrows):
            x_offset = 0
            for col in range(nrow):
                idx = row * nrow + col
                if idx < len(images):
                    grid_image.paste(images[idx], (x_offset, y_offset))
                    x_offset += max_widths[col]
            y_offset += max_heights[row]
        grid_image.save(filepath)
    
    def parse_prompt(self, prompt, parser_mode=None):
        parser_mode = parser_mode or self.mode
        if parser_mode == 'old':
            return self.parser.paraphrase2(prompt)
        else:
            return self.parser.parse(prompt)
    
    def query_search(self, query):
        with torch.no_grad(), torch.amp.autocast('cuda'):
            D_e5, I_e5 = self.e5_search("query: " + query, self.e5_model, self.e5_index, 500)
            e5_result = pd.DataFrame({"score": D_e5[0]}, index=I_e5[0])
            D_clip, I_clip = self.clip_search(query, self.clip_tokenizer, self.clip_model, self.clip_index, 500)
            clip_result = pd.DataFrame({"score": D_clip[0]}, index=I_clip[0])
            result = e5_result.join(clip_result, how="inner", lsuffix="_e5", rsuffix="_clip")
            result["score"] = result["score_e5"] + result["score_clip"]
            result = result.join(self.metadata, how="inner")
            result.sort_values(by="score", ascending=False, inplace=True)
        return result
    
    def tag_search(self, parsed_prompt):
        raise NotImplementedError
    
    def search(self, prompt, search_mode=None):
        search_mode = search_mode or self.mode
        tags, artists, parsed_prompt = self.parse_prompt(prompt, parser_mode=search_mode)
        if search_mode == 'old':
            results = self.query_search(parsed_prompt)
        else:
            results = self.query_search(parsed_prompt)
        return tags, artists, results
    
    def generate_exhibition(self, prompt, search_mode='phrase'):
        if not os.path.exists(os.path.join(OUTPUT_DIR, prompt)):
            os.makedirs(os.path.join(OUTPUT_DIR, prompt))
        tags, artists, result = self.search(prompt, search_mode)
        filtered_result = self.filter_search_results(tags, artists, result)
        result = filtered_result.iloc[:60]
        curator = ExhibitionCurator(api_key="your key", metadata=self.metadata)
        exhibitions = curator.curate(result, query=prompt)
        for i, exhibition in enumerate(exhibitions):
            with open(os.path.join(OUTPUT_DIR, prompt, f'Exhibition_{i}.json'), 'w') as f:
                json.dump(exhibition, f, indent=4)
            self.save_images(os.path.join(OUTPUT_DIR, prompt, f'Exhibition_{i}.jpg'), exhibition['art_pieces'])

if __name__ == "__main__":
    agent = Prompt_exhibition_generator()
    while True:
        prompt = input("Prompt to search: ")
        if prompt.lower() in ['exit', 'quit', 'bye']:
            break
        if not os.path.exists(os.path.join(OUTPUT_DIR, prompt)):
            os.makedirs(os.path.join(OUTPUT_DIR, prompt))
        tags, artists, result = agent.search(prompt, search_mode='phrase')
        result = result.iloc[:50]
        curator = ExhibitionCurator(api_key="your key", metadata=agent.metadata)
        exhibitions = curator.curate(result)
        for i, exhibition in enumerate(exhibitions):
            with open(os.path.join(OUTPUT_DIR, prompt, f'Exhibition_{i}.json'), 'w') as f:
                json.dump(exhibition, f, indent=4)
            agent.save_images(os.path.join(OUTPUT_DIR, prompt, f'Exhibition_{i}.jpg'), exhibition['art_pieces'])