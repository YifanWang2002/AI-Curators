import os
from datetime import datetime
from openai import OpenAI

client = OpenAI()

def upload_jsonl_file(file_path):
    # Upload the JSONL file
    batch_input_file = client.files.create(
        file=open(file_path, "rb"),
        purpose="batch"
    )
    print("Batch input file uploaded with ID:", batch_input_file.id)
    return batch_input_file.id

def create_batch(batch_input_file_id, log_folder="batch_logs"):
    # Create the batch using the uploaded file ID
    batch = client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={"description": "Batch processing artwork descriptions from nga and artic"}
    )

    print("Batch created with ID:", batch.id)
    
    # Ensure the log folder exists
    os.makedirs(log_folder, exist_ok=True)
    
    # Generate a timestamp for the log file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save the batch ID to a log file with the timestamp in the name
    log_file_name = f"batch_id_log_{timestamp}.txt"
    log_file_path = os.path.join(log_folder, log_file_name)
    with open(log_file_path, "a") as log_file:
        log_file.write(f"Batch ID: {batch.id}\n")
    
    return batch

def retrieve_batch(batch_id):
    # Retrieve the batch status
    batch = client.batches.retrieve(batch_id)
    print("Batch status:", batch)

if __name__ == "__main__":

    jsonl_path = 'artworks_jsonl_file.jsonl'

    batch_input_file_id = upload_jsonl_file(jsonl_path)

    batch = create_batch(batch_input_file_id)

    # Retrieve the batch status
    # retrieve_batch('batch_vPr1MaOWzKpstebU0ZJOfQAr')
