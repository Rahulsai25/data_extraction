from dotenv import load_dotenv
import os

load_dotenv()  # Load .env file

# Debug: Print the API key to check if it's loaded
api_key = os.getenv("GOOGLE_API_KEY")
if api_key is None:
    print("API Key not found. Please check your .env file.")
else:
    print(f"API Key successfully loaded: {api_key}")
