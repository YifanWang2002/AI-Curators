# Import Statements
import streamlit as st
import requests
import json
import html
from modules import *
from st_clickable_images import clickable_images
import streamlit as st
import json
import html

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

st.markdown(f'''
    <style>
    section[data-testid="stSidebar"] .css-ng1t4o {{width: 14rem;}}
    </style>
''',unsafe_allow_html=True)

DEV = True
MAX_ART = 15

if DEV:
    backend_url = "http://127.0.0.1:8000"





# Page Title and Description
st.header("Your Personalized Art Recommendations 🌟")
channel = st.radio(
    "Discover Your Art Adventure 🧙‍♂️",
    options=[
        "ArtMatch: Tailored Art Recommendations",
        "ArtSpace: Create Your Personalized Exhibition"
    ],
    help="Select 'ArtMatch' for personalized art suggestions based on your tastes, or 'ArtSpace' to curate and design your own virtual art exhibition."
)

# Display Recommendations
def get_recommendation(user_name:str, n=15):
    '''
    Fetch recommendations from backend and display them
    '''
    response = requests.get(f"{backend_url}/get_recommendation_by_profile", params={"n": n, "user_name": user_name})
    recommendations = response.json() 
    return recommendations

def curate_exhibition(prompt:str, n=15):
    '''
    Fetch recommendations from backend and display them
    '''
    response = requests.get(f"{backend_url}/get_recommendation_by_prompt", params={"n": n, "prompt": prompt})
    recommendations = response.json() 
    return recommendations

def render_art_recommendations(json_response):
    if 'clicked_art_id' not in st.session_state:
        st.session_state.clicked_art_id = None

    # Streamlit page setup with custom JavaScript for redirect
    st.markdown("""
    <style>
    /* CSS for layout and hover effect */
    .image-container {
        position: relative;
        width: 80%;
        margin-top: 20px;
        margin-bottom: 20px;
        display: flex;
        justify-content: flex-end;
    }
    .image-text {
        position: absolute;
        bottom: 10px;
        left: 10px;
        color: white;
        padding: 5px;
        background-color: rgba(0, 0, 0, 0.5);
        visibility: hidden;
        opacity: 0;
        transition: visibility 0s, opacity 0.5s linear;
    }
    .image-container:hover .image-text {
        visibility: visible;
        opacity: 1;
    }
    </style>
    <script>
    function directRedirect(targetUrl) {
        // Directly redirect to the target URL
        window.open(targetUrl, '_blank');
    }
    </script>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap='small')
    columns = [col1, col2]

    for index, rec in enumerate(json_response):
        details = rec["details"]
        file_id = details["FILE"].split('.')[0]
        title = details["TITLE"]
        author = details["AUTHOR"]
        external_url = "http://localhost:8501/Voice_Tutor"  # This is the target URL for redirection
        # Assuming get_image_by_id is defined to fetch image data
        image_data = get_image_by_id(file_id)

        # Include an onclick event that directly calls the redirect function
        image_html = f"""
            <div class="image-container">
                <img src='data:image/jpeg;base64,{image_data}' style='width:100%; object-fit:contain; cursor:pointer;' onclick="directRedirect('{external_url}')"/>
                <div class="image-text">{html.escape(title)} by {html.escape(author)}</div>
            </div>
        """

        col = columns[index % 2]

        with col:
            st.markdown(image_html, unsafe_allow_html=True)

if channel == "ArtMatch: Tailored Art Recommendations":
    if 'user_name' in st.session_state:
        st.markdown("Based on your viewing history and preferences, we've curated some artworks for you.")
        render_art_recommendations(get_recommendation(user_name=st.session_state.user_name, n=MAX_ART))
    else:
        st.warning("Please enter your name and finish the user profiling questions to get started.")
else: 
    st.info("Please be as specific as possible, and you will get more accurate results. \nTry: 'apple, still life, oil painting'.")
    prompt = st.text_input("🔮 What would you like to see today?")
    st.info("Our app might show some inaccurate results because we're still training our AI and expanding our collection of royalty-free art images. Rest assured, our tech team is working hard to improve accuracy and provide better art recommendations by March.")
    if prompt:
        st.success(f"showing arts related to {prompt}")
        render_art_recommendations(curate_exhibition(prompt, n=MAX_ART))



