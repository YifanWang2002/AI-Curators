import os
from PIL import Image

# Global settings
Image.MAX_IMAGE_PIXELS = None

def compress_image(input_path, output_path, target_size_mb):
    quality = 90  # Starting quality
    step = 5      # Step to decrease quality
    img = Image.open(input_path)
    img.save(output_path, 'JPEG', quality=quality)  # Initial save to ensure it exists
    
    while os.path.getsize(output_path) > target_size_mb * 1024 * 1024:
        quality -= step
        img.save(output_path, 'JPEG', quality=quality)
        if quality < 10:
            break

def create_thumbnail(input_path, thumbnail_path):
    with Image.open(input_path) as img:
        aspect = img.width / img.height
        if img.width < img.height:  
            new_height = int(100 / aspect)
            img = img.resize((100, new_height), Image.LANCZOS)
        else:  # Landscape
            new_width = int(100 * aspect)
            img = img.resize((new_width, 100), Image.LANCZOS)
        
        center_x, center_y = img.width // 2, img.height // 2
        img = img.crop((center_x - 50, center_y - 50, center_x + 50, center_y + 50))
        img.save(thumbnail_path, 'JPEG')

if __name__ == '__main__':
    source_folder = 'images'
    target_folder = 'images_compressed'
    thumbnail_folder = 'thumbnails'

    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    if not os.path.exists(thumbnail_folder):
        os.makedirs(thumbnail_folder)

    all_files = os.listdir(source_folder)
    for filename in all_files:
        file_path = os.path.join(source_folder, filename)
        target_path = os.path.join(target_folder, filename)
        thumbnail_path = os.path.join(thumbnail_folder, filename)

        if os.path.getsize(file_path) > 10 * 1024 * 1024:
            compress_image(file_path, target_path, 9.8)
        else:
            Image.open(file_path).save(target_path)

        create_thumbnail(file_path, thumbnail_path)

    print("Compression and thumbnail creation complete.")
