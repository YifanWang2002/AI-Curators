# SeeM Data Cleaning Process

Welcome to the second phase of our data pipeline at SeeM. Following the collection of artwork images and related metadata under the CC0 license, this phase focuses on preparing the data for integration into our virtual gallery.

## Purpose

This phase is structured to ensure the data is accurate, consistent, and ready for display. Key tasks include:

1. Standardizing metadata across different sources.
2. Removing duplicates and irrelevant data.
3. Ensuring high-quality image standards.

## Requirements

### Folder Structure

Maintain the following directory structure for organization and consistency:

```code
02_data_cleaning\
|--Museum_name_Month_Date\
|   |--Museum_name_clean_data.py
|   |--Museum_name_cleaned_data.csv
|   |--Museum_name_processed_images\
|   |--Other_Case_Specific_Files
```

### Data Cleaning Steps

1. **Metadata Standardization:**
   - Ensure that all metadata fields such as `title`, `artist`, `date`, and `medium` are standardized across different museum datasets. Use a uniform format for dates and artist names. (Please See [Appendix](#appendix---mongodb-data-schemas-for-seem-art-collection))

2. **Duplicate Removal:**
   - Implement checks to identify and remove duplicate records in the data based on artwork titles and artist names.

3. **Legal Check:**
   - Make sure images and textual metadata are all available under the CC0 license.


## Process Checklist

Use this table to track the progress of each step in the data cleaning process for the listed museums. Update the checkboxes and notes as you complete each task.

| Museum                       | Metadata Standardized | Duplicates Removed | Images Validated |  Optional Notes              |
|------------------------------|-----------------------|--------------------|------------------|------------------------------|
| National Gallery of Art      | [ ]                   | [ ]                | [ ]              |                              |
| Metropolitan Museum of Art   | [ ]                   | [ ]                | [ ]              |                              |
| Art Institute of Chicago     | [ ]                   | [ ]                | [ ]              |                              |
| Cleveland Museum of Art      | [ ]                   | [ ]                | [ ]              |                              |
| J. Paul Getty Museum         | [ ]                   | [ ]                | [ ]              |                              |



## Appendix - MongoDB Data Schemas for SeeM Art Collection

This document outlines the final data models for our collections in MongoDB. Please ensure that as much data as possible is natively sourced from CSV files and modify their variable names accordingly.

### Artworks Collection Schema

**Collection Name**: `artworks`

- **Properties**:
  - **artist_id**: `string`
  - **artwork_id**: `string`
  - **title**: `string`
  - **genre**: `string`
  - **location**: `string`
  - **description**: `string`
  - **creation_year_start**: `string`
  - **creation_year_end**: `string`
  - **dimension**: `string`
  - **full_image_url**: `string`
  - **thumbnail_image_url**: `string`
  - **views**: `int`
  - **likes**: `int`
  - **intro**: `string` - An elegant description of the artwork.
  - **overview**: `string` - Depicts what is shown in the artwork.
  - **style**: `string` - The style of the artwork.
  - **style_tags**: `string` - Style tags of the artwork.
  - **theme**: `array` of `string`
  - **theme_tags**: `array` of `string`
  - **main_objects**: `object` - Description of main objects within the artwork.
  - **other_objects**: `array` of `string`
  - **movement**: `array` of `string`
  - **object_tags**: `array` of `string`
  - **tags**: `array` of `string`
  - **nudity**: `string` - Indicates the level of nudity depicted in the artwork. Options: `full`, `half`, `no`.
  - **religious**: `bool`


### Artists Collection Schema

**Collection Name**: `artists`

- **Properties**:
  - **artist_id**: `string`
  - **biography**: `string`
  - **birth_year**: `string`
  - **death_year**: `string`
  - **display_name**: `string`
  - **first_name**: `string`
  - **full_name**: `string`
  - **last_name**: `string`
  - **middle_name**: `string`
  - **nationality**: `string`
  - **thumbnail_image_url**: `string`
  - **views**: `int`
  - **likes**: `int`


