# Exhibition Curator

A tool for curating art exhibitions using AI-powered search.

## Prerequisites
- Python 3.10
- MongoDB
- Docker
- Required Python packages (install via `pip install -r requirements.txt`)

## Setup
1. Run Docker
2. Ensure MongoDB is running and accessible

## How to Use
1. Change the `DATABASE_URL` in `data.py` to your MongoDB connection string
2. Modify the prompt in `run.py`
   - Example: `prompt = "I like Vincent's sad artwork"`
3. Run the application: `python run.py`

## Project Structure
```
data/
├── dimension_tables/    # (not used anymore - replaced by MongoDB)
│   ├── dim_artwork.csv
│   ├── dim_tag.csv
│   └── mapping_tag_artwork.csv
├── index_files/        # (still used for search functionality)
│   ├── name_index.index      # FAISS index for artwork name search
│   ├── tag_index.index       # FAISS index for tag-based search
│   └── description_embeddings.npy  # Pre-computed artwork description embeddings
└── prompt_based_exhibition/      # Core exhibition generation logic
      ├── ArtSearch.py
      ├── exhibition_curator.py
      └── prompt_parser_beta.py
data.py                      # Database interaction layer
run.py                      # Application entry point
```

#### prompt_based_exhibition/
Core logic for exhibition generation
- `ArtSearch.py`: Search implementation
- `exhibition_curator.py`: Exhibition generation logic
- `prompt_parser_beta.py`: Prompt handling and parsing
