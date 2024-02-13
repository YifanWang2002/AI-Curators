import streamlit as st

st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                }
        </style>
        """, unsafe_allow_html=True)

st.header("AI Tutor - Coming March")

st.info("Our technical team is deeply committed to developing this new feature. Due to its complexity and our ongoing efforts to gather more data, we anticipate fully launching this feature by March.")

st.markdown(
    '''
     **AI Art Tutor 🎓** will feature the below features:
    - **Reliable Knowledge Bot**: Utilizing Azure's AI Language Services, our chatbot is designed to deliver trustworthy responses to users' inquiries. At the core of this service is the Retrieval-Augmented Generation (RAG) technology, 
    which functions akin to an exceptionally knowledgeable digital librarian. This system meticulously searches through an extensive and credible database of textbooks and scholarly articles, ensuring that the information provided is 
    detailed and accurate.
    
    - **Voice Assitant**: Implementing Azure's Speech services for high-accuracy speech-to-text, text-to-speech, and real-time translation features to cater to a wider, more diverse audience.
    We also plan to create AI avatars of renowned artists crafted from historical records of their personalities and personal stories. This interactive Q&A feature with the artists will enhance the educational enjoyment for users. 
    Moreover, our multilingual translations will ensure inclusivity, offering a seamless experience for a global audience.

    - **Artwork Advice & Inspiration**: Utilizing Azure's AI capabilities, including GPT's vision and DALL-E 3's image generation, to offer personalized advice and creative inspirations based on user-submitted artwork and requirements.
       
'''
)