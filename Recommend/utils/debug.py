import os
from PIL import Image

IMAGE_DIR = "../GPT/images"


def save_images(filepath, image_ids, nrow=5):
    # Load images
    images = [
        Image.open(os.path.join(IMAGE_DIR, f"{image_id}.jpg")) for image_id in image_ids
    ]

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
    # print(f"Image saved as {filepath}")
