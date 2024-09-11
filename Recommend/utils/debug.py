import os
import requests
from PIL import Image

IMAGE_DIR = "images"


def save_images(filepath, image_ids, urls=None, nrow=5):
    # Load images
    images = []
    for i, image_id in enumerate(image_ids):
        image_path = os.path.join(IMAGE_DIR, f"{image_id}.jpg")
        if not os.path.exists(image_path):
            try:
                response = requests.get(urls.iloc[i])
                if response.status_code == 200:
                    with open(image_path, "wb") as f:
                        f.write(response.content)
                else:
                    print(f"Failed to download image {image_id}: Response code {response.status_code}")
                    continue
            except Exception as e:
                print(f"Failed to download image {image_id}: {e}")
                continue
        image = Image.open(image_path)
        images.append(image)
    if len(images) == 0:
        print("No images to save")
        return
    # Calculate the size of the grid
    nrows = (len(images) + nrow - 1) // nrow
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
