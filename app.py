import streamlit as st
import os
import pathlib
import textwrap
from PIL import Image
import vertexai
from vertexai.preview.generative_models import (
    GenerationConfig,
    GenerativeModel
)
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Initialize the Streamlit page config at the very beginning
st.set_page_config(page_title="Gemini Image Demo")

# Rest of your setup and code

PROJECT_ID = os.getenv("gen-ai-model-deployment")
REGION = os.getenv("us-central1 (Iowa)")
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

vertexai.init(project=PROJECT_ID, location=REGION)

print("Ok")

# Function to load OpenAI model and get responses
def get_gemini_response(input, image, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash-002')
    response = model.generate_content([input, image[0], prompt])
    return response.text

# Function to handle the uploaded image
def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        # Read the file into bytes
        bytes_data = uploaded_file.getvalue()

        image_parts = [
            {
                "mime_type": uploaded_file.type,  # Get the mime type of the uploaded file
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")

# Initializing our streamlit app

st.header("Gemini Application")
input = st.text_input("Input Prompt: ", key="input")
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
image = ""   
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image.", use_container_width=True)

submit = st.button("Tell me about the image")

input_prompt = """
               You are an expert in understanding invoices.
               You will receive input images as invoices &
               you will have to answer questions based on the input image
               """

# If ask button is clicked
if submit:
    image_data = input_image_setup(uploaded_file)
    response = get_gemini_response(input_prompt, image_data, input)
    st.subheader("The Response is")
    st.write(response)
