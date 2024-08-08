# SeeM Image Processing Process

Welcome to the third phase of our data pipeline at SeeM. In this phase, we focus on the processing and storage of images that have been collected and cleaned in the previous stages. Our aim is to prepare these images for optimal use in our virtual gallery, ensuring they are available in multiple resolutions for different viewing and interactive experiences.

## Purpose
This phase involves resizing and uploading the artwork images to Azure Blob Storage in three distinct sizes:

1. Original Size
2. Smaller Size for GPT (the batch api request endpoint has a <10mb file limit for vision api).
3. Thumbnail Size.

# SeeM Image Processing Process

Welcome to the third phase of our data pipeline at SeeM. In this phase, we focus on the processing and storage of images that have been collected and cleaned in the previous stages. Our aim is to prepare these images for optimal use in our virtual gallery, ensuring they are available in multiple resolutions for different viewing and interactive experiences.

## Purpose

This phase involves resizing and uploading the artwork images to Azure Blob Storage in three distinct sizes:

1. **Original Size**: Preserve the images in their original resolution for archival purposes and high-quality displays.
2. **Smaller Size for GPT**: Adapt images to a smaller resolution suitable for use with our Generative Pre-trained Transformer models for AI interactions.
3. **Thumbnail Size**: Create small, quick-loading versions of the images for previews and faster browsing experiences.

## Requirements

### Tools Used

- **Python**: Utilizing libraries such as Pillow for image resizing and Azure SDK for Python to handle uploads to Azure Blob Storage.
- **Azure Blob Storage**: For securely storing and managing the different image sizes.

### Folder Structure


```code
03_image_processing\
|--image_preprocessing.py
|--azure_upload.py
```

### Image Processing Steps

1. **Resizing Images**:
   - Use scripts to resize images to the required dimensions for GPT and thumbnail use cases.
   - Ensure the original image quality is maintained when storing the 'original size' images.

2. **Uploading to Azure**:
   - Configure Azure Blob Storage to categorize and store images based on their sizes.
   - Ensure proper security measures and access controls are in place to protect the data.

