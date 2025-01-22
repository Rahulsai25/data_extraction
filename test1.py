import streamlit as st
import os
import pathlib
import textwrap
from PIL import Image
from dotenv import load_dotenv
import boto3
from datetime import datetime


# Load environment variables
load_dotenv()

import google.generativeai as genai

# Load and print the API Key for debugging
api_key = os.getenv("Google_Api_Key")
if not api_key:
    raise ValueError("API Key not found! Please set the Google_Api_Key in your .env file.")
print(f"API Key: {api_key}")  # For debugging

# Configure API
genai.configure(api_key=api_key)

## Function to load Gemini AI model and get responses
def get_gemini_response(input, image, prompt):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([input, image[0], prompt])
        return response.text
    except Exception as e:
        raise ValueError(f"Error generating response from Gemini AI: {e}")

## Function to process uploaded images
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

## Function to upload data to S3
def upload_to_s3(bucket_name, file_name, data, profile_name="Rahulsai"):
    try:
        # Create a session using the specified profile
        session = boto3.Session(profile_name=profile_name)
        s3 = session.client('s3')
        
        # Upload the data to the S3 bucket
        s3.put_object(Bucket=bucket_name, Key=file_name, Body=data)
        print(f"File {file_name} successfully uploaded to {bucket_name}")
    except Exception as e:
        raise ValueError(f"Error uploading to S3: {e}")

## Initializing Streamlit app
st.set_page_config(page_title="Gemini Image Demo")

st.header("Gemini Application")
input = st.text_input("Input Prompt: ", key="input")
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
image = ""   
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image.")

submit = st.button("Tell me about the image")

input_prompt = """
               You are an expert in understanding invoices.
               You will receive input images as invoices &
               you will have to answer questions based on the input image
               """

if submit:
    try:
        # Process the uploaded image
        image_data = input_image_setup(uploaded_file)
        
        # Get the Gemini AI response
        response = get_gemini_response(input_prompt, image_data, input)
        
        # Display the response in the app
        st.subheader("The Response is")
        st.write(response)
        
        # Save response to S3
        bucket_name = "gemini-app-responses"  # Replace with your S3 bucket name
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"response_{timestamp}.txt"
        upload_to_s3(bucket_name, file_name, response)
        
        # Show success message
        st.success(f"Response saved to S3 bucket: {bucket_name}, File: {file_name}")
    except Exception as e:
        st.error(f"Error: {e}")
