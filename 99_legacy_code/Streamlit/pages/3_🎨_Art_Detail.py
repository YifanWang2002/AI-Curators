import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image
import pandas as pd
import os
from modules import *
from pathlib import Path

st.set_page_config(layout = 'wide')

# show_sidebar()

st.markdown("""
        <style>
               .block-container {
                    padding-top: 2rem;
                    padding-bottom: 0rem;
                }
        </style>
        """, unsafe_allow_html=True)



ask = False

col11, col12, col13 = st.columns([1, 5, 1])

current_dir = Path(__file__).parent

# Load metadata
base_image_path = current_dir.parent / 'data' / 'art_images'
metadata_path = current_dir.parent / 'data' / 'art_metadata.csv'
metadata = pd.read_csv(metadata_path)

# Create image options from metadata
image_options = metadata.apply(lambda row: (f"{row.name}: {row['TITLE']} by {row['AUTHOR']} ({row['FILE']})", row.name), axis=1).tolist()
image_options_dict = {row.name: row['FILE'] for index, row in metadata.iterrows()}

st.info('''Currently, streamlit capabilities do not support redirect from the previous page to the Art Detail Page. 
            Thus, in order to simulate real user interaction, you may manually select the artworks we recommended for you earlier or browse through our collections.
            We're actively working on enhancing our platform by migrating to a more robust front-end framework. 
            This upgrade will soon enable you to explore each artwork in depth. We appreciate your understanding and are 
            excited to bring you these improved features in the near future!''', icon="ℹ️")

with col11:
    upload_choice = st.radio("Choose an image source:", ("Select from Gallery", "Upload Image"))

image_options = [(index, f"{row['TITLE']} by {row['AUTHOR']} ({row['FILE']})") for index, row in metadata.iterrows()]

# In the Streamlit app
with col12:
    if upload_choice == "Select from Gallery":
        # Note: Use index as the option value and custom format function for display
        selected_index = st.selectbox(
            'Select an Image:',
            options=[option[0] for option in image_options],  # Use indices as options
            format_func=lambda x: next((text for index, text in image_options if index == x), "")
        )
        selected_row = metadata.loc[selected_index]
        selected_file_name = selected_row['FILE']
        target_image_path = os.path.join(base_image_path, selected_file_name)
        img = Image.open(target_image_path)
    elif upload_choice == "Upload Image":
        img_file = st.file_uploader("Upload a file", type=['png', 'jpg'], key="file_uploader")
        if img_file:
            img = Image.open(img_file)
    

with col13:
    box_color = st.color_picker("Box Color", value='#0000FF')


col21, col22, col23 = st.columns([2,3,1],gap="small")

with col21:
    target_height = 300
    if 'img' in locals():
        aspect_ratio = img.width / img.height
        new_height = target_height
        new_width = int(new_height * aspect_ratio)
        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        cropped_img = st_cropper(resized_img, realtime_update=True, box_color=box_color)


col31, col32 = st.columns([1,8])

with col31:
    st.text("")
    if 'cropped_img' in locals():
        cropped_img.thumbnail((150,150))  
        st.image(cropped_img)
        ask = st.button("Explain this")

with col32:
    with st.container(height=250):
        if ask:
            prompt = f'''You are a professional art instructor, you are given a painting {selected_row["TITLE"]} by {selected_row["AUTHOR"]}, 
                    with a cropped section from it. Please analyze from a professional art appreciation's perspective, what's the cropped image, 
                    and if there's anything worth mentioning. Start the analyze on the cropped section immediately. Your response should be concise and straight to the point.
                    '''
            base64_cropped_img = encode_image_pil(cropped_img)
            base64_resized_img = encode_image_pil(resized_img)
            with st.chat_message("Artist", avatar = "👩‍🎨"):
                st.write(ask_gpt_vision(prompt=prompt, images=[base64_cropped_img,base64_resized_img], max_token=200))
                # st.write('''The cropped section of "Madonna and Child between Sts Andrew and Prosper" by Benozzo Gozzoli portrays the Child, presumably Jesus, in a tender and human pose. Noteworthy is the naturalism of the Child's body and the sense of weight as He leans on the Madonna's lap, demonstrating Gozzoli's skill in rendering the human form with a sense of three-dimensionality. His positioning and the halo around His head are indicative of the centrality of divine figures in religious Renaissance art. The delicate details, like the fine lines of the hair and the soft modeling of the flesh, along with the use of gold to denote holiness, reflect Gozzoli's finesse and the fine aesthetics of the time. The rich colors and the attention to textural details, like the translucency of the fabric, show Gozzoli's attention to both human form and the adornment of his subjects.''')



