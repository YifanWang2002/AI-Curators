# Import Modules
import streamlit as st
import os
import base64
import requests
from io import BytesIO

def get_image_by_id(image_id):
    '''
    Fetch image by id, return base64 encoded image
    '''
    image_path = os.path.join("data","art_images",f"{image_id}.jpg")
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def encode_image_pil(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")  
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def ask_gpt_vision(prompt: str, images: list, max_token = 300):
    """
    Ask GPT with vision capability about a list of images.

    Parameters:
    - prompt: str. The question or prompt to ask about the images.
    - images: list. A list of base64-encoded images.

    Returns:
    - The response from the API.
    """
    # OpenAI API Key from Streamlit secrets
    api_key = st.secrets["OA_API_KEY_2"]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Start constructing the payload with the initial prompt
    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}]
        }
    ]

    # For each image, add it to the message content
    for idx, image_base64 in enumerate(images):
        # Add the image
        messages[0]["content"].append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        })

    # Construct the final payload
    payload = {
        "model": "gpt-4-vision-preview",
        "messages": messages,
        "max_tokens": max_token
    }

    # Make the request to the OpenAI API
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    
    # Return the response JSON
    response = response.json()
    
    try:
        # Check if the expected keys and paths exist in the response
        if "choices" in response and len(response["choices"]) > 0:
            message = response["choices"][0].get("message", {})
            content = message.get("content", "")
            
            # Check if the content is not empty
            if content:
                return content
            else:
                return "The response does not contain message content."
        else:
            return "The response format is incorrect or missing expected data."
    except Exception as e:
        return f"An error occurred while processing the response: {e}"

def show_sidebar():
    with st.sidebar:
        if 'user_name' not in st.session_state:
            user_name = st.text_input("👋What's your name?")
            if user_name:
                st.session_state.user_name = user_name
                st.success(f"Hello {user_name}! You may start your art journey!")
        else:
            user_name = st.session_state.user_name
            st.success(f"Hello {user_name}! You may start your art journey!")
            switch = st.button("Switch User")
            if switch:
                del st.session_state.user_name
                st.experimental_rerun()