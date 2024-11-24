import os
import json
import pandas as pd
import requests
from PIL import Image, ImageTk
import tkinter as tk
from io import BytesIO
from math import ceil

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
        
        # Load data and display images
        self.load_and_display(exhibition_path, artwork_data_path)

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

    def save_gallery(self):
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gallery_exports')
        os.makedirs(output_dir, exist_ok=True)
        
        # Get the bbox of all items in the canvas
        bbox = self.scrollable_frame.bbox()
        
        # Create a new image with the size of the frame
        image = Image.new('RGB', (bbox[2]-bbox[0], bbox[3]-bbox[1]), 'white')
        
        # Save the widget as PostScript first
        temp_ps = os.path.join(output_dir, "temp.ps")
        self.scrollable_frame.update()
        self.scrollable_frame.postscript(file=temp_ps)
        
        # Convert PostScript to PNG
        img = Image.open(temp_ps)
        output_path = os.path.join(output_dir, f'gallery_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.png')
        img.save(output_path, 'PNG')
        
        # Clean up temporary file
        os.remove(temp_ps)
        print(f"Gallery saved to: {output_path}")

def main():
    root = tk.Tk()
    root.geometry("900x800")
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths
    exhibition_file = os.path.join(current_dir, 'output', 'I like countryside artwork', 'Exhibition_0.json')
    artwork_data_file = os.path.join(current_dir, 'data', 'dimension_tables', 'dim_artwork.csv')
    
    app = ArtworkGallery(root, exhibition_file, artwork_data_file)
    root.mainloop()

if __name__ == "__main__":
    main()