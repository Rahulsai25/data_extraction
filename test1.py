import streamlit as st
import os
import json
import boto3
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

# Function to upload file to S3
def upload_to_s3(file_data, bucket_name="gemini-app-responses", s3_key="data/data1.json"):
    try:
        # Initialize boto3 client
        s3_client = boto3.client('s3')

        # Create the file locally (JSON format)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = f"response_{timestamp}.json"
        
        # Save the response as a JSON file
        with open(file_path, 'w') as json_file:
            json.dump(file_data, json_file)
        
        # Upload to S3
        s3_client.upload_file(file_path, bucket_name, s3_key)
        
        print(f"File {file_path} uploaded successfully to {bucket_name} with key {s3_key}.")
    except Exception as e:
        print(f"Error uploading file to S3: {e}")

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
        image_data = input_image_setup(uploaded_file)
        
        # Get the Gemini AI response
        response_text = get_gemini_response(input_prompt, image_data, input)
        
        # Display the response in the app
        st.subheader("The Response is")
        st.write(response_text)
        
        # Prepare the response for uploading to S3
        response_data = {
            "input": input,
            "response": response_text
        }

        # Upload the response to S3 as a JSON file
        s3_key = f"data/response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        upload_to_s3(response_data, s3_key=s3_key)
        
        # Notify user of success
        st.success(f"Response saved to S3 bucket: {bucket_name}, File: {s3_key}")
    except Exception as e:
        st.error(f"Error: {e}")
