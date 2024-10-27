# Exhibition Curator

A tool for curating art exhibitions using AI-powered search.

### Prerequisites
- Python 3.10
- MongoDB
- Required Python packages (install via `pip install -r requirements.txt`):
- docker

2. Ensure MongoDB is running and accessible

### Run
```
python run.py
```

### File Structure

data/
├── dimension_tables/  (not used anymore - replaced by MongoDB)
│   ├── dim_artwork.csv
│   ├── dim_tag.csv
│   └── mapping_tag_artwork.csv
├── index_files/       (still used for search functionality)
│   ├── name_index.index      # FAISS index for artwork name search
│   ├── tag_index.index       # FAISS index for tag-based search
│   └── description_embeddings.npy  # Pre-computed artwork description embeddings
|
prompt_based_exhibition/      # Core exhibition generation logic
|     ├── ArtSearch.py
|     ├── exhibition_curator.py
|     ├── prompt_parser_beta.py
|
data.py                      # Database interaction layer
|    ├── functions to fetch data from MongoDB 
run.py                       # Application entry point
|    ├── main file to run the program 
|    ├── calling functions from data.py and prompt_based_exhibition

### Features
- AI-powered artwork search using FAISS indices
- Semantic similarity matching for artwork descriptions
- Tag-based artwork filtering
- MongoDB integration for efficient data storage and retrieval

