import streamlit as st
import os
from dotenv import load_dotenv
import boto3
from datetime import datetime
from PIL import Image
import google.generativeai as genai

# Load environment variables from .env file
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

# Function to upload data to S3
def upload_to_s3(bucket_name, file_name, data):
    print(f"DEBUG: upload_to_s3 called with bucket_name={bucket_name}, file_name={file_name}")
    try:
        # Create a boto3 session with the credentials from .env
        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        s3 = session.client('s3')
        s3.put_object(Bucket=bucket_name, Key=file_name, Body=data)
        print(f"DEBUG: File {file_name} successfully uploaded to {bucket_name}")
    except Exception as e:
        print(f"ERROR: Error uploading to S3: {e}")
        raise

# Streamlit app initialization
st.set_page_config(page_title="Gemini Image Demo")
st.header("Gemini Application")

# User input prompt
input = st.text_input("Input Prompt: ", key="input")
print(f"DEBUG: Input prompt received: {input}")

# File uploader
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
print(f"DEBUG: Uploaded file: {uploaded_file}")

image = ""   
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image.")
    print(f"DEBUG: Image loaded: {image}")

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
        
        # Save response to S3
        bucket_name = "gemini-app-responses"  # Replace with your S3 bucket name
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"response_{timestamp}.txt"
        print(f"DEBUG: S3 upload details - bucket: {bucket_name}, file_name: {file_name}")
        upload_to_s3(bucket_name, file_name, response)
        
        # Show success message
        st.success(f"Response saved to S3 bucket: {bucket_name}, File: {file_name}")
    except Exception as e:
        st.error(f"Error: {e}")
        print(f"ERROR: Exception occurred: {e}")
