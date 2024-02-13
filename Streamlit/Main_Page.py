# Import Modules
import requests
import pandas as pd
import streamlit as st
from glob import glob
# from streamlit_image_annotation import detection
# import cv2
import numpy  as np
import urllib.request
# import torch
import os
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                }
        </style>
        """, unsafe_allow_html=True)

DEV = True

if DEV:
    backend_url = "http://127.0.0.1:8000"



st.title("AI Curators 🖼️")


with st.expander("Introduction 🚀", expanded=True):
    st.markdown("""
    **Welcome to our cutting-edge web application where art meets AI! We're at the forefront of integrating advanced AI technologies to redefine 
    how art is experienced and appreciated. Our platform leverages the power of AI to bring a new dimension to art education and engagement, 
    making it more accessible, interactive, and enjoyable for all.**

    **Mission**: Our mission is centered around harnessing AI to enhance art education and accessibility. We aim to bridge the gap in art education, 
                especially for underprivileged students and those who lack access to essential resources. By utilizing AI-driven tools, we're committed 
                to providing immersive and customized educational experiences that foster creativity and engagement with art in a way that was previously unattainable.

    **Vision**: Our vision is to create a world where every individual has the opportunity to engage with and learn from art in a deeply personal and meaningful way. 
                Through the use of AI, we envision transforming traditional art education into a more dynamic, interactive, and personalized experience. 
                Our platform is designed to transcend geographical and socioeconomic barriers, bringing the world of art to everyone's fingertips.

    **Value**: We value innovation, inclusivity, and the transformative power of AI in education and the arts. Our approach emphasizes not only providing access to art 
                but also enriching the learning experience through interactive and AI-powered features. We're dedicated to creating a sustainable ecosystem where art lovers, 
                students, and artists alike can explore, learn, and connect with art in novel ways.
    """)


with st.expander("User Guide 📄"):
    st.subheader("User Profiling 🕵️‍♀️")
    st.write("""
    We use user profiling to learn more about your art preferences. This interactive tool helps you explore various artworks, and based on your selections, we gain insights into your artistic tastes. Here's how it works:

    **How to Use This Tool**
    1. **Start Your Art Journey**: Enter your name in the sidebar to begin.
    2. **Explore Artworks**: You will be presented with a series of artworks. For each set, choose the one that resonates with you the most.
    3. **Progress Through Questions**: There are a total of 10 questions, each offering a different set of artworks, double click on the image to confirm your selection.
    4. **Review Your Selections**: After completing all questions, you can review the artworks you selected.
    5. **Submit Your Preferences**: Your selections will be submitted automatically, helping us tailor future art recommendations for you.

    **Features**
    - **Art Selection**: **Double** Click on the artwork that you like the most.
    - **Progress Tracking**: The display keeps track of how many questions you've answered.
    - **Review and Reset**: At any time, you can review your choices and reset them if needed.

    Embark on this journey to discover art that speaks to you and let us help you find more of what you love!
    """)
   
    st.subheader("Art Recommendation 🔮")
    st.write("""
    Based on the interactive profiling and your selections, we offer two unique ways to discover art that aligns with your taste:
    
    **ArtMatch**: Tailored Art Recommendations
    - **Personalized Selections**: Artworks recommended specifically for you, based on your responses.
    - **Diverse Artworks**: A range of styles, periods, and artists, ensuring a rich and varied experience.
    - **Direct Interaction**: Click on any artwork to explore it further or learn more about the artist.
    
    **ArtSpace**: Create Your Personalized Exhibition
    - **Curate Your Gallery**: Enter a prompt or theme, and we'll present artworks that match your concept.
    - **Design Your Exhibition**: Ideal for those who love to explore themes or create narrative journeys through art.
    - **Explore and Expand**: A great way to discover new artworks and artists that align with specific themes or ideas.

    Whether you're exploring your personal tastes with 'ArtMatch' or creating thematic collections with 'ArtSpace', we aim to provide an engaging and enlightening experience. Enjoy exploring the world of art tailored to your preferences!
""")
    
    st.info('''Currently, streamlit capabilities do not support direct clicks for more details on curated artworks. 
            However, we're actively working on enhancing our platform by migrating to a more robust front-end framework. 
            This upgrade will soon enable you to explore each artwork in depth. We appreciate your understanding and are 
            excited to bring you these improved features in the near future!''', icon="ℹ️")


    st.subheader("Art Details 🖼️")
    st.write('''
        Explore the intricate details of artworks with our "Art Details" feature. Utilize AI for an in-depth analysis of selected or uploaded art pieces.
           
        **How to Use**:
        1. **Image Source Selection**: Choose 'Select from Gallery' for curated artworks or 'Upload Image' for personal images.
        2. **Selecting/Uploading an Image**: For gallery images, select from titles and authors. For uploads, PNG or JPG formats are supported.
        3. **Interactive Cropping**: Focus on specific parts of the artwork using our cropping tool. Customize the box color for better visibility.
        4. **AI-Powered Analysis**: After cropping, hit "Explain this" to receive insights from an AI mimicking a professional art instructor’s perspective.

        **Features**:
        - **Cropping Tool**: Customize your area of interest on the artwork.
        - **AI Analysis**: Get expert-like explanations on the cropped section.
        - **Gallery or Personal Uploads**: Flexibility in image choice.
        - **Box Color Customization**: Enhance cropping visibility with color adjustments.

        **Tips**:
        - Explore various artwork sections with the cropping tool.
        - Adjust the box color for a clearer cropping experience.
        - Leverage this feature to gain insights into diverse art styles and artists.
    ''')

    st.subheader("Art Tutor 👩‍🏫")
    st.write("Your personal AI art tutor designed to answer all your questions about art...")


with st.expander("Future Work: Expanding Horizons with AI and Azure 🚀"):
    st.write('''
    *Our technical team is deeply committed to developing those features. Due to their complexity and our ongoing efforts to gather more data, we anticipate continuously rolling out those features starting from March.*
    1. **AI Art Tutor 🎓**:
    - **Reliable Knowledge Bot**: Utilizing Azure's AI Language Services, our chatbot is designed to deliver trustworthy responses to users' inquiries. At the core of this service is the Retrieval-Augmented Generation (RAG) technology, 
    which functions akin to an exceptionally knowledgeable digital librarian. This system meticulously searches through an extensive and credible database of textbooks and scholarly articles, ensuring that the information provided is 
    detailed and accurate.

    - **Voice Assitant**: Implementing Azure's Speech services for high-accuracy speech-to-text, text-to-speech, and real-time translation features to cater to a wider, more diverse audience.
    We also plan to create AI avatars of renowned artists crafted from historical records of their personalities and personal stories. This interactive Q&A feature with the artists will enhance the educational enjoyment for users. 
    Moreover, our multilingual translations will ensure inclusivity, offering a seamless experience for a global audience.

    - **Artwork Advice & Inspiration**: Utilizing Azure's AI capabilities, including GPT's vision and DALL-E 3's image generation, to offer personalized advice and creative inspirations based on user-submitted artwork and requirements.
       
    2. **AI Learning System 📚**:
       - **Incentive System**: Implementing an Azure-based incentive system akin to Duolingo. This system will set up tasks and rewards to encourage users to engage more with our platform.
    
    3. **3D Model Generation 🌐**:
       - **3D Gaussian Splatting with Diffusion Models**: Utilizing Azure's advanced AI and machine learning services to generate digitized models of museum collections from video clips, employing techniques like 3D Gaussian Splatting combined with diffusion models.

    4. **Intriguing Educational Games 🎮**:
       - **Style Transfer**: Leveraging Azure's Cognitive Services for artistic style transfer in games.
       - **Find the AI-Generated Imposter**: Creating games where users identify AI-generated artworks, using Azure's AI capabilities.
       - **Coloring Book Generation**: Generating coloring books from famous artworks using Azure's AI image generation tools.
       - **AI Persona of Famous Artists**: Creating interactive AI personas of famous artists using Azure's AI services, including RAG (Retrieval-Augmented Generation) technology for animated conversations about their experiences and artworks.

    Our journey ahead is focused on harnessing these advanced Azure AI services to enhance the educational and artistic experience for users worldwide.
    ''')


with st.expander("References & Acknowledgements 👏"):
    st.write("We owe a huge thank you to Microsoft Founders Hub who sponsored the Azure and OpenAI credits for necessary dataset preparating, model development and web application deployment. ")
