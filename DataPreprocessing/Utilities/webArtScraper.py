from selenium import webdriver
from bs4 import BeautifulSoup
from rich.progress import Progress, MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn
import pandas as pd
import time
import requests
import os

total_pages = 1923
artworks_per_page = 30

def download_image(image_url, filename, folder='nga_images'):
    if not os.path.exists(folder):
        os.makedirs(folder)
    path = os.path.join(folder, filename)
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            with open(path, 'wb') as file:
                file.write(response.content)
            return path
    except Exception as e:
        print(f"Error downloading image {filename}: {e}")
    return None

def get_text_safe(element, default='Unknown'):
    return element.get_text(strip=True) if element else default

def scrape_artwork_data(page_source, progress, artwork_task):
    soup = BeautifulSoup(page_source, 'html.parser')
    artworks = soup.find_all('li', {'class': 'art'})

    for artwork in artworks:
        try:
            title = get_text_safe(artwork.find('dt', {'class': 'title'}))
            author = get_text_safe(artwork.find('dt', {'class': 'artist'}))
            year = get_text_safe(artwork.find('dd', {'class': 'created'}))
            medium = get_text_safe(artwork.find('dd', {'class': 'medium'}))
            description = artwork.find('img', {'class': 'thumbnail'})['alt'].strip() if artwork.find('img', {'class': 'thumbnail'}) else 'No description'
            image_element = artwork.find('li', {'class': 'tool-download'}).find('a')
            image_url = image_element['href'] if image_element else 'No URL'

            image_path = download_image(image_url, f"{title.replace(' ', '_')}.jpg") if image_url != 'No URL' else 'No image'

            # Writing to CSV here
            header = not os.path.exists('artwork_data.csv')
            df = pd.DataFrame([[title, author, year, medium, description, image_path]], columns=['Title', 'Author', 'Year', 'Medium', 'Description', 'Image_Path'])
            df['Image_Path'] = df['Image_Path'].apply(lambda x: os.path.basename(x) if x else x)  # Store only filename
            df.to_csv('artwork_data.csv', mode='a', header=header)

            progress.update(artwork_task, advance=1)
        except Exception as e:
            print(f"Error processing artwork: {e}")

# Selenium setup
driver = webdriver.Chrome()

progress_columns = [
    *Progress.get_default_columns(),
    MofNCompleteColumn(),
    TimeElapsedColumn(),
    TimeRemainingColumn()
]

with Progress(*progress_columns) as progress:
    page_task = progress.add_task("[cyan]Going Through Pages ...", total=total_pages)
    artwork_task = progress.add_task("[green]Going Through Arts ...", total=artworks_per_page)

    for page_number in range(1, total_pages + 1):
        driver.get(f"https://www.nga.gov/collection-search-result.html?sortOrder=DEFAULT&artobj_downloadable=Image_download_available&pageNumber={page_number}&lastFacet=artobj_downloadable")
        time.sleep(10)  # Wait for dynamic content to load
        page_source = driver.page_source

        progress.reset(artwork_task)  # Reset artwork progress for the new page
        scrape_artwork_data(page_source, progress, artwork_task)
        progress.advance(page_task)

driver.quit()
