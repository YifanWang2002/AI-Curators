# SeeM Data Collection Process

Welcome to the initial phase of our data pipeline. At SeeM, we curate artwork images that are available under the CC0(Creative Commons) license and integrate them into our database for showcasing in our virtual gallery.

## Purpose

This phase is designed to:

1. Identify artwork resources licensed under CC0.
2. Acquire images through API requests or web scraping.

## Requirements

### Commonly Used Tools
We'll largely rely on Google search to identify artwork resources licensed under CC0 and acquire the data on a case-by-case basis. This may involve accessing museums' GitHub repositories for open data available in JSON or CSV files, and at other times, we'll need to iteratively call the API endpoints.


### Folder Structure
Please organize your project files using the following directory structure:

```code
01_data_collection\
|--Museum_name_Month_Date\
|   |--Museum_name_get_csv.py
|   |--Museum_name_get_image.py
|   |--Museum_name_collections.csv
|   |--Museum_name_images\
|   |--Other_Case_Specific_Files
```

### Data Collection Scope
Ensure that the `Museum_name_collections.csv` contains records for every artifact or item from the museum. This comprehensive collection enables easy expansion into other genres in the future. However, restrict image downloads to artworks categorized under painting and watercolor genres, which are often labeled as "oil on canvas," "painting," or "watercolor."


## Museum Checklist with CC0 Resources
Use this table to track the progress of each step in the data collection process for the listed museums. Update the checkboxes and notes as you complete each task.

| Museum                       | CSV Collected | Images Collected |  Optional Notes              |
|------------------------------|---------------|------------------|------------------------------|
| National Gallery of Art      | [x]           | [x]              |                              |
| Metropolitan Museum of Art   | [x]           | [x]              |                              |
| Art Institute of Chicago     | [x]           | [x]              |                              |
| Cleveland Museum of Art      | [x]           | [x]              |                              |
| J. Paul Getty Museum         | [ ]           | [ ]              |                              |



