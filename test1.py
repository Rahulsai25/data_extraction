import streamlit as st
import os
import json
import pdf2image
from PIL import Image
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

import google.generativeai as genai

# Load and print the API Key for debugging
api_key = os.getenv("Google_Api_Key")
if not api_key:
    raise ValueError("API Key not found! Please set the Google_Api_Key in your .env file.")
print(f"API Key: {api_key}")  # For debugging

# Configure API
genai.configure(api_key=api_key)

## Function to load OpenAI model and get responses
def get_gemini_response(input, image, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([input, image[0], prompt])
    return response.text

def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        image_parts = [
            {
                "mime_type": uploaded_file.type,  
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")

## Initializing Streamlit app
st.set_page_config(page_title="Gemini Image Demo")

st.header("Gemini Application")
input = st.text_input("Input Prompt: ", key="input")
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "pdf"])
image = ""   

if uploaded_file is not None:
    # If the uploaded file is a PDF, convert it to PNG
    if uploaded_file.type == "application/pdf":
        # Convert PDF to images (png format)
        pages = pdf2image.convert_from_bytes(uploaded_file.read(), fmt="png")
        # Save the first page as a PNG image (can handle more if needed)
        image = pages[0]
    else:
        # Handle image files directly
        image = Image.open(uploaded_file)
    
    # Proceed with your logic for the image
    st.image(image, caption="Uploaded Image", use_column_width=True)


submit = st.button("Tell me about the image")

input_prompt = """
               You are an expert in understanding invoices.
               You will receive input images as invoices &
               you will have to answer questions based on the input image
               """

if submit:
    try:
        image_data = input_image_setup(uploaded_file)
        
        # Get the Gemini AI response
        response_text = get_gemini_response(input_prompt, image_data, input)
        
        # Display the response in the app
        st.subheader("The Response is")
        st.write(response_text)
        
    except Exception as e:
        st.error(f"Error: {e}")
