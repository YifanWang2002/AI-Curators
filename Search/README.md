# Search Engine

Basic Search Engine: Lucene with default algorithm (BM25).

Query Augmentation: Using Gemini API.

Compiling
```shell
mvn clean package
```

Indexing
```shell
java -jar target/search-1.0-SNAPSHOT.jar --index
```

I put the artwork embeddings into the index, so the indexing process takes about half a minute (otherwise it takes less than 1 second). But the `analysis` field is the only thing used for searching now–embeddings and other fields are not used.

Searching
```shell
export GEMINI_API_KEY="AIzaSyDmkAKSOdjV98XT_jEGChFu4yUHOoGLMps" # better replace the value with your own api key
java -jar target/search-1.0-SNAPSHOT.jar --search
```

Input your query after the prompt. The program will run both augmented search and non-augmented search, so you can compare their results. (Please use the output titles to find the urls in the art_metadata.csv file manually.)

Sometimes their results are not very different. But the augmented search is useful for 
- Considering some synonyms: if you enter "sad", it will also search for "sorrowful", "unhappy", etc.
- Correcting some typos: if you enter "friut oli painting", it knows you are talking about "fruit oil painting".