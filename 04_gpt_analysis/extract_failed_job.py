import json
import os
from datetime import datetime



# Define paths to the files
error_file_path = 'batch_error_log.jsonl'
original_file_path = 'original_file_path.jsonl'

# Function to read all errors and collect their custom IDs
def collect_failed_custom_ids(error_file_path):
    failed_custom_ids = set()
    with open(error_file_path, 'r') as file:
        for line in file:
            error_entry = json.loads(line)
            failed_custom_ids.add(error_entry['custom_id'])
    return failed_custom_ids

# Function to extract failed requests from the original file using collected IDs
def extract_failed_requests(original_file_path, failed_ids):
    failed_requests = []
    with open(original_file_path, 'r') as file:
        for line in file:
            request = json.loads(line)
            if request['custom_id'] in failed_ids:
                failed_requests.append(request)
    return failed_requests

# Collecting failed custom IDs
failed_custom_ids = collect_failed_custom_ids(error_file_path)

# Extracting failed requests
failed_requests = extract_failed_requests(original_file_path, failed_custom_ids)

# Saving the failed requests to a new JSONL file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

new_request_file_path = f'resubmit_failed_requests_{timestamp}.jsonl'
with open(new_request_file_path, 'w') as new_file:
    for request in failed_requests:
        new_file.write(json.dumps(request) + '\n')
