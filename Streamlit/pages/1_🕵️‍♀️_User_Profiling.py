import streamlit as st
from st_clickable_images import clickable_images
import requests
from modules import *
from models import profileResponseModel
from PIL import Image
import io
import base64
from models import *

st.set_page_config(layout = 'wide')

show_sidebar()

st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                }
        </style>
        """, unsafe_allow_html=True)



# Parameters
NQUESTIONS = 10
DEV = True
if DEV:
    backend_url = "http://127.0.0.1:8000"

# Display Questions
def get_questions():
    '''
    Fetch question from backend and display them for user choice
    '''
    response = requests.get("http://backend-url/questions")
    questions = response.json()

    user_responses = []
    for question in questions:
        choice = st.radio(question["text"], question["options"])
        user_responses.append({"question_id": question["id"], "choice": choice})

    return user_responses
# Submit Responses
def submit_responses(user_responses):
    '''
    Submit responses to backend and get user profile
    '''
    response = requests.post("http://backend-url/responses", json=user_responses)
    if response.status_code == 200:
        st.success("Responses submitted successfully")
    else:
        st.error("Failed to submit responses")


# User Interface
# TODO: Add a title and description for the page, define a function to get user choices

# Streamlit page configuration




st.header("Discover Your Artistic Preferences")
st.write(f"""
Welcome to our interactive art exploration! Embark on a journey of artistic discovery, where each step reveals more about your unique taste in art.
- **View a Series of Artworks:** For each of the {NQUESTIONS} questions, we'll present you with four artworks.
- **Select What Resonates:** Choose the artwork that speaks to you the most—trust your instincts.
- **Uncover Your Artistic Taste:** Your selections help us understand your artistic preferences.
Your choices will guide us in tailoring future art recommendations specifically for you, ensuring a personalized experience that resonates with your individual taste. Let's begin this artistic adventure!
""")

if 'user_name' not in st.session_state:
    st.warning("Please enter your name in the sidebar to start the art journey.")

if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0

if 'user_responses' not in st.session_state:
    st.session_state.user_responses = []

# Fetch all questions only once
if 'all_questions' not in st.session_state:
    st.session_state.all_questions = requests.get(f"{backend_url}/questions").json()['questions']

if st.session_state.current_question_index < NQUESTIONS:
    current_question = st.session_state.all_questions[st.session_state.current_question_index]
    question_id = current_question["question_id"]
    choice_image_id = [choice["image_id"] for choice in current_question["choices"]]
    images = []

    for id in choice_image_id:
        image_data = get_image_by_id(id)  
        images.append(f"data:image/jpeg;base64,{image_data}")

    clicked = clickable_images(
        images,
        titles=[f"Image #{i+1}" for i in range(len(images))],
        div_style={
            "display": "flex", 
            "justify-content": "center", 
            "flex-wrap": "nowrap"  # Change from 'wrap' to 'nowrap'
        },
        img_style={
            "margin": "5px", 
            "height": "200px", 
            "object-fit": "cover",
            "flex": "0 0 auto"  # Ensure images do not grow or shrink
        }
    )
    if st.session_state.current_question_index < NQUESTIONS-1:
        st.write(f"Questions remaining: {NQUESTIONS - st.session_state.current_question_index}")

    # Handle image click
    if clicked > -1:
        selected_choice = current_question["choices"][clicked]
        st.session_state.user_responses.append(profileResponseModel(
            question_id=question_id,
            choice_image_id=selected_choice["image_id"],
            choice_image_title=selected_choice["image_title"]
        ))

        # Move to the next question
        if st.session_state.current_question_index < NQUESTIONS - 1:
            st.session_state.current_question_index += 1
        else:
            st.session_state.current_question_index = NQUESTIONS

elif st.session_state.current_question_index == NQUESTIONS:
    # Display completion message and show selected images or results
    st.markdown("🎉 :red[All questions complete, you have selected the following art. Please go to the next page to see recommendations.]")
    
    def display_selected_images():
        num_rows = len(st.session_state.user_responses) // 5 + (len(st.session_state.user_responses) % 5 > 0)
        for i in range(num_rows):
            cols = st.columns(5)
            for j in range(5):
                index = i * 5 + j
                if index < len(st.session_state.user_responses):
                    response = st.session_state.user_responses[index]
                    image_data = get_image_by_id(response.choice_image_id)
                    image_bytes = io.BytesIO(base64.b64decode(image_data))
                    image = Image.open(image_bytes)
                    cols[j].image(image, caption=f"{response.choice_image_title}", use_column_width=True)
    
    display_selected_images()  # Display the images selected by the user


    if 'user_name' not in st.session_state:
        user_name = "guest_login"
    else:
        user_name = st.session_state.user_name

    post_data = {
        "user_name": user_name,
        "responses": [response.dict() for response in st.session_state.user_responses]
    }

    # Send POST request to the FastAPI endpoint
    response = requests.post(f"{backend_url}/responses", json=post_data)

    # Handle the response
    if response.status_code == 200:
        st.success("Responses submitted successfully!")
        # Further actions upon successful submission
    else:
        st.error("Failed to submit responses. Please try again.")


if st.button("Reset Selections"):
    st.session_state.current_question_index = 0
    st.session_state.user_responses = []
    st.experimental_rerun()  