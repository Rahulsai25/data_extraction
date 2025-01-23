import streamlit as st
import os
import json
import pdf2image
from PIL import Image
from dotenv import load_dotenv
from datetime import datetime
import boto3
import google.generativeai as genai

load_dotenv()

# Load AWS credentials from .env file
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')

# Load Google API Key
api_key = os.getenv("Google_Api_Key")
if not api_key:
    raise ValueError("API Key not found! Please set the Google_Api_Key in your .env file.")
print(f"DEBUG: API Key loaded: {api_key}")

# Configure Google API
genai.configure(api_key=api_key)

# Function to load Gemini AI model and get responses
def get_gemini_response(input, image, prompt):
    print(f"DEBUG: get_gemini_response called with input={input}, prompt={prompt}")
    print(f"DEBUG: Image data: {image}")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([input, image[0], prompt])
        print(f"DEBUG: Response generated: {response.text}")
        return response.text
    except Exception as e:
        print(f"ERROR: Failed to generate response: {e}")
        raise

# Function to process uploaded images
def input_image_setup(uploaded_file):
    print(f"DEBUG: input_image_setup called with uploaded_file={uploaded_file}")
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        image_parts = [
            {
                "mime_type": uploaded_file.type,
                "data": bytes_data
            }
        ]
        print(f"DEBUG: Processed image data: {image_parts}")
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")

# Streamlit app initialization
st.set_page_config(page_title="Gemini Image Demo")
st.header("Gemini Application")

# User input prompt
input = st.text_input("Input Prompt: ", key="input")
print(f"DEBUG: Input prompt received: {input}")

# File uploader (including PDFs)
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "pdf"])
print(f"DEBUG: Uploaded file: {uploaded_file}")

image = ""
if uploaded_file is not None:
    # If the uploaded file is a PDF, convert it to PNG
    if uploaded_file.type == "application/pdf":
        # Convert PDF to images (png format)
        pages = pdf2image.convert_from_bytes(uploaded_file.read(), fmt="png")
        # Save the first page as a PNG image
        image = pages[0]
        print(f"DEBUG: PDF converted to image, first page extracted.")
    else:
        # Handle image files directly
        image = Image.open(uploaded_file)
        print(f"DEBUG: Image loaded: {image}")
    
    # Display the image in Streamlit
    st.image(image, caption="Uploaded Image.", use_column_width=True)

submit = st.button("Tell me about the image")
print(f"DEBUG: Submit button clicked: {submit}")

input_prompt = """
               You are an expert in understanding invoices.
               You will receive input images as invoices &
               you will have to answer questions based on the input image
               """
print(f"DEBUG: Input prompt for model: {input_prompt}")

if submit:
    try:
        # Process the uploaded image
        image_data = input_image_setup(uploaded_file)
        
        # Get the Gemini AI response
        response = get_gemini_response(input_prompt, image_data, input)
        
        # Display the response in the app
        st.subheader("The Response is")
        st.write(response)
        print(f"DEBUG: Displayed response: {response}")
        
    except Exception as e:
        st.error(f"Error: {e}")
        print(f"ERROR: Exception occurred: {e}")
