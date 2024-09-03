import os
import requests
import time
import pandas as pd


def download_image(url, save_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            file.write(response.content)
        return True
    else:
        return False


if __name__ == "__main__":
    destination_folder = "data/painting_images"

    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    count = {"success": 0, "fail": 0}
    failed_uuids = []

    df = pd.read_csv("data/artworks.csv")
    for url, artwork_id in zip(df["full_image_url"], df["artwork_id"]):
        image_save_path = os.path.join(destination_folder, f"{artwork_id}.jpg")
        if download_image(url, image_save_path):
            time.sleep(0.1)
            count["success"] += 1
        else:
            print(url)
            failed_uuids.append(artwork_id)
            count["fail"] += 1

    df = df[~df["image_id"].isin(failed_uuids)]
    df.to_csv("data/paintings_with_images.csv", index=False)
    print(count)
    # {'success': 1371, 'fail': 380}
