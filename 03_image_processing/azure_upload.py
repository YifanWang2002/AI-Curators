import os
from azure.storage.blob import BlobServiceClient

def upload_file_to_azure(file_path, container_client, blob_path):
    blob_client = container_client.get_blob_client(blob_path)
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

if __name__ == '__main__':
    connection_string = 'YOUR_CONNECTION_STRING'
    container_name = "AZURE_CONTAINER_NAME"
    sub_folder = ""

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    target_folder = 'images_compressed'
    thumbnail_folder = 'thumbnails'

    all_files = os.listdir(target_folder)
    for filename in all_files:
        original_file_path = os.path.join(target_folder, filename)
        compressed_file_path = os.path.join(target_folder, filename)
        thumbnail_file_path = os.path.join(thumbnail_folder, filename)

        # Upload original image
        blob_path = os.path.join(sub_folder, 'original', filename)
        upload_file_to_azure(original_file_path, container_client, blob_path)

        # Upload compressed image
        blob_path = os.path.join(sub_folder, 'compressed', filename)
        upload_file_to_azure(compressed_file_path, container_client, blob_path)

        # Upload thumbnail
        blob_path = os.path.join(sub_folder, 'thumbnails', filename)
        upload_file_to_azure(thumbnail_file_path, container_client, blob_path)

    print("All files uploaded to Azure successfully.")
