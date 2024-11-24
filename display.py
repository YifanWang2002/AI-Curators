import os
import json
import pandas as pd
import requests
from PIL import Image, ImageTk
import tkinter as tk
from io import BytesIO
from math import ceil
import requests
import math
import os

class ArtworkGallery:
    def __init__(self, root, exhibition_path: str, artwork_data_path: str):
        self.root = root
        self.root.title("Art Exhibition Gallery")
        
        # Create main canvas with scrollbar
        self.main_frame = tk.Frame(root, bg='white')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.main_frame, bg='white')
        self.scrollbar = tk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='white')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack scrollbar and canvas
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Load the data
        with open(exhibition_path, 'r') as f:
            self.exhibition = json.load(f)
        self.df_artwork = pd.read_csv(artwork_data_path)
        # Store exhibition name for later use
        self.name = exhibition_path.split('/')[-2:]
        
        # Load data and display images
        self.load_and_display(exhibition_path, artwork_data_path)
        self.create_catalog_export()
    
    def create_catalog_export(self):
        """Create and save the A4 catalog version of the exhibition"""
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample/gallery_exports')
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, f'{self.name}.pdf')
        
        create_artwork_catalog(
            artwork_ids=self.exhibition['art_pieces'],
            df_artwork=self.df_artwork,
            exhibition_info=self.exhibition,
            output_path=output_path
        )
        print(f"Catalog saved to: {output_path}")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(-1 * int((event.delta / 120)), "units")

    def load_and_display(self, exhibition_path: str, artwork_data_path: str):
        # Read the exhibition JSON file
        with open(exhibition_path, 'r') as f:
            exhibition = json.load(f)
        
        # Read the artwork dimension table
        df_artwork = pd.read_csv(artwork_data_path)
        
        # Get artwork IDs from exhibition
        artwork_ids = exhibition['art_pieces']
        
        # Display exhibition title
        title_label = tk.Label(
            self.scrollable_frame,
            text=exhibition['title'],
            font=("Helvetica", 16, "bold"),
            bg='white',
            wraplength=800
        )
        title_label.pack(pady=20)
        
        # Create description label
        desc_label = tk.Label(
            self.scrollable_frame,
            text=exhibition['description'],
            font=("Helvetica", 10),
            bg='white',
            wraplength=800,
            justify=tk.LEFT
        )
        desc_label.pack(pady=(0, 20))

        # Calculate grid layout
        images_per_row = 3
        current_row_frame = None
        current_column = 0

        # Keep reference to PhotoImage objects
        self.photo_references = []

        for idx, artwork_id in enumerate(artwork_ids):
            # Create new row frame if needed
            if current_column == 0:
                current_row_frame = tk.Frame(self.scrollable_frame, bg='white')
                current_row_frame.pack(pady=10)

            # Get artwork URL from dimension table
            artwork_url = df_artwork[df_artwork['artwork_id'] == artwork_id]['small_image_url'].iloc[0]
            
            try:
                # Download and process image
                response = requests.get(artwork_url)
                img = Image.open(BytesIO(response.content))
                
                # Resize image while maintaining aspect ratio
                target_size = (250, 250)
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # Create white background
                bg = Image.new('RGB', target_size, 'white')
                offset = ((target_size[0] - img.size[0]) // 2, (target_size[1] - img.size[1]) // 2)
                bg.paste(img, offset)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(bg)
                self.photo_references.append(photo)
                
                # Create frame for image and title
                img_frame = tk.Frame(current_row_frame, bg='white')
                img_frame.pack(side=tk.LEFT, padx=10)
                
                # Display image
                label = tk.Label(img_frame, image=photo, bg='white')
                label.pack()
                
                # Display artwork ID below image
                id_label = tk.Label(img_frame, text=artwork_id, bg='white', wraplength=200)
                id_label.pack()
                
                current_column = (current_column + 1) % images_per_row
                
            except Exception as e:
                print(f"Error processing {artwork_id}: {e}")
                current_column = (current_column + 1) % images_per_row

def create_artwork_catalog(artwork_ids, df_artwork, exhibition_info, output_path):
    """
    Create a catalog of artwork images laid out on A4-sized pages.
    
    Args:
        artwork_ids (list): List of artwork IDs to include
        df_artwork (pd.DataFrame): DataFrame containing artwork information
        exhibition_info (dict): Exhibition details including title and description
        output_path (str): Path to save the output file
    """
    # A4 size in pixels at 300 DPI
    A4_WIDTH = 2480  # 210mm * 300DPI / 25.4
    A4_HEIGHT = 3508  # 297mm * 300DPI / 25.4
    
    # Define margins and spacing
    MARGIN = 150
    SPACING = 50
    
    # Calculate usable area
    usable_width = A4_WIDTH - (2 * MARGIN)
    usable_height = A4_HEIGHT - (2 * MARGIN)
    
    # Define image size
    IMAGE_SIZE = (600, 600)  # Target size for each artwork image
    
    # Calculate how many images can fit per row and column
    images_per_row = math.floor(usable_width / (IMAGE_SIZE[0] + SPACING))
    images_per_column = math.floor(usable_height / (IMAGE_SIZE[1] + SPACING))
    images_per_page = images_per_row * images_per_column
    
    # Calculate total pages needed
    total_pages = math.ceil(len(artwork_ids) / images_per_page)
    
    # Create pages
    pages = []
    for page_num in range(total_pages):
        # Create white background
        page = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), 'white')
        
        # Add header on first page
        if page_num == 0:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(page)
            
            # Try to load a font, fall back to default if not available
            try:
                title_font = ImageFont.truetype("arial.ttf", 60)
                desc_font = ImageFont.truetype("arial.ttf", 40)
            except:
                title_font = ImageFont.load_default()
                desc_font = ImageFont.load_default()
            
            # Draw title
            draw.text((MARGIN, MARGIN), exhibition_info['title'], 
                     fill='black', font=title_font)
            
            # Draw description with word wrap
            desc_words = exhibition_info['description'].split()
            desc_lines = []
            current_line = []
            for word in desc_words:
                current_line.append(word)
                if len(' '.join(current_line)) * 10 > usable_width:  # Approximate width
                    desc_lines.append(' '.join(current_line[:-1]))
                    current_line = [word]
            if current_line:
                desc_lines.append(' '.join(current_line))
            
            for i, line in enumerate(desc_lines):
                draw.text((MARGIN, MARGIN + 100 + i*50), line, 
                         fill='black', font=desc_font)
            
            # Adjust starting position for images
            start_y = MARGIN + 100 + (len(desc_lines) + 1) * 50
        else:
            start_y = MARGIN
        
        # Calculate which images go on this page
        start_idx = page_num * images_per_page
        end_idx = min((page_num + 1) * images_per_page, len(artwork_ids))
        
        # Place images
        for i, artwork_id in enumerate(artwork_ids[start_idx:end_idx]):
            row = i // images_per_row
            col = i % images_per_row
            
            # Calculate position
            x = MARGIN + col * (IMAGE_SIZE[0] + SPACING)
            y = start_y + row * (IMAGE_SIZE[1] + SPACING)
            
            try:
                # Get artwork URL and download image
                artwork_url = df_artwork[df_artwork['artwork_id'] == artwork_id]['small_image_url'].iloc[0]
                response = requests.get(artwork_url)
                img = Image.open(BytesIO(response.content))
                
                # Resize image while maintaining aspect ratio
                img.thumbnail(IMAGE_SIZE, Image.Resampling.LANCZOS)
                
                # Create white background for individual image
                img_bg = Image.new('RGB', IMAGE_SIZE, 'white')
                offset = ((IMAGE_SIZE[0] - img.size[0]) // 2, 
                         (IMAGE_SIZE[1] - img.size[1]) // 2)
                img_bg.paste(img, offset)
                
                # Add image ID below the artwork
                draw = ImageDraw.Draw(img_bg)
                try:
                    font = ImageFont.truetype("arial.ttf", 30)
                except:
                    font = ImageFont.load_default()
                draw.text((10, IMAGE_SIZE[1] - 40), f"ID: {artwork_id}", 
                         fill='black', font=font)
                
                # Paste onto page
                page.paste(img_bg, (x, y))
                
            except Exception as e:
                print(f"Error processing artwork {artwork_id}: {e}")
        
        pages.append(page)
    
    # Save all pages
    if len(pages) == 1:
        pages[0].save(output_path)
    else:
        pages[0].save(output_path, save_all=True, append_images=pages[1:])

def main():
    root = tk.Tk()
    root.geometry("900x800")
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths
    exhibition_file = os.path.join(current_dir, 'output', 'I like flowers', 'Exhibition_2.json')
    artwork_data_file = os.path.join(current_dir, 'data', 'dimension_tables', 'dim_artwork.csv')
    
    app = ArtworkGallery(root, exhibition_file, artwork_data_file)
    root.mainloop()

if __name__ == "__main__":
    main()