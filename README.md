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

## Architecture
```
[Data API Container (port 8000)]
         ↑
         | HTTP calls
         ↓
[This Exhibition API Container (port 5000)]
```
## setup env
1. create `.env` file
2. add your OpenAI API key as `OPENAI_API_KEY`

## How to Use (non-API)
1. Change the `DATABASE_URL` in `data.py` to your MongoDB connection string
2. Modify the prompt in `run.py`
   - Example: `prompt = "I like Vincent's sad artwork"`
3. Run the application: `python run.py`

## Call the API (flask)
1. `python api.py`
2. Send a POST request using:     
```bash
curl -X POST \
  http://localhost:5001/api/generate_exhibition \
  -H "Content-Type: application/json" \
  -d '{"prompt": "modern art with flowers"}'
```
3. Change the prompt as you like

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
├── prompt_based_exhibition/      # Core exhibition generation logic
│   ├── ArtSearch.py
│   ├── exhibition_curator.py
│   └── prompt_parser_beta.py
├── api.py                  # New API layer for the application
├── Dockerfile              # Docker configuration file
├── docker-compose.yml      # Docker Compose configuration file
├──  data.py                      # Database interaction layer
├── run.py                      # Application entry point
├── api.py                  # API layer for the application
├── Dockerfile              # Docker configuration file
├── docker-compose.yml      # Docker Compose configuration file
└── requirements.txt
```

## build docker and run (use `docker-compose` or `docker compose`)
1. `docker compose up --build` (build and run)
      - Start API-data first (in data repo)
      - `cd api-data/docker`
      - `docker compose up -d`
            - image: `mongo-latest`: 27017:27017
            - image: `docker-flask-app`: 8000:5000
      - Then start API-exhibition (in this repo)
      - `cd AI-Curators/`
      - `docker compose up -d`
            - image: `ai-curators-api`: 5000:5000
2. `docker compose up -d` (detached mode)
3. `docker compose down` (stop and remove containers)
4. load data to MongoDB using curl in [dump-the-files](https://github.com/Metaverse-Museum/Back-End-Python?tab=readme-ov-file#dump-the-files)
5. check data api
      - `curl http://localhost:8000/api/data/artworks  # Works - data API`
6. check exhibition api
      - ```bash
        curl -X POST http://localhost:5000/api/generate_exhibition \
             -H "Content-Type: application/json" \
             -d '{"prompt": "I like vincent'\''s sad artwork"}'
        ```

## rebuild docker if you change the Dockerfile
```bash
docker compose down
docker compose build
docker compose up -d
```

#### prompt_based_exhibition/
Core logic for exhibition generation
- `ArtSearch.py`: Search implementation
- `exhibition_curator.py`: Exhibition generation logic
- `prompt_parser_beta.py`: Prompt handling and parsing
