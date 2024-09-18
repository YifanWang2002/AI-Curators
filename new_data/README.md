## Useful Data

- `artwork_with_tags.csv`: all artwork info with processed tags (`tags` column)
- `tag_count_type.csv`: all (final) tags with their count and type
- `tag_embeddings.npy`: embeddings of tags, with the same order as the tags in `tag_count_type.csv`
    - Encoded with CLIP's text encoder.

## Debug Only Data

- `artwork_with_gpt.csv`: all artwork info after running gpt and before adding tags
- `all_tag_embeddings.csv`: embeddings of all tags (10000+) before deduplication
- `tag_mapping.csv`: substitutions made during deduplication