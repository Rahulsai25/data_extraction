import sys
sys.path.append("/mnt/efs/python")

import os
import json
import time
import boto3
from io import BytesIO
from PIL import Image
import google.generativeai as genai

# ✅ Load API Key
API_KEY = os.getenv("Api_key1")
if not API_KEY:
    raise ValueError("❌ API Key not found!")

print("✅ API Key loaded successfully.")

# ✅ Configure Gemini API
genai.configure(api_key=API_KEY)
print("✅ Google Gemini API configured.")

# ✅ Configure AWS S3
s3 = boto3.client("s3")
print("✅ AWS S3 client initialized.")

# ✅ Define S3 bucket names
INPUT_BUCKET = "flask-image-api-bucket1"
OUTPUT_BUCKET = "json-extracted-output"
OUTPUT_FOLDER = "json_files/"
print(f"📌 Input Bucket: {INPUT_BUCKET}, Output Bucket: {OUTPUT_BUCKET}/{OUTPUT_FOLDER}")

# ✅ Define AI Prompt
INPUT_PROMPT = """
You are an expert in extracting data from invoices.
Please extract the following features from the input and return them in JSON format:
UHID, IP No (Inpatient Number), Date of Admission (DOA), Date of Discharge (DOD), Treating Doctor, Consultant, 
Admission No, Bed No, Billing Class, Room Type, Pan No, GST No, Bill Date, From Date, To Date, Total Bill Amount, 
Deposit Amount, Net Bill Amount, Total Payable Amount, Outstanding Amount, Bill No, Invoice No, GSTIN, Patient Name, 
Hospital Name, Diagnostic Name, Age, Gender, Diagnosis, Date, Doctor Name, Referring Doctor, Required Amount, City, DOB, 
Patient Number, Govt Allotted Number, Address, Phone Number, Father's Name.

If a field is not present, set it to null.
Additionally, extract any other fields found in the invoice that are not part of the predefined list.
"""

# ✅ Predefined keys for extraction
PREDEFINED_KEYS = [
    "UHID", "IP No (Inpatient Number)", "Date of Admission (DOA)", "Date of Discharge (DOD)", "Treating Doctor",
    "Consultant", "Admission No", "Bed No", "Billing Class", "Room Type", "Pan No", "GST No", "Bill Date", "From Date",
    "To Date", "Total Bill Amount", "Deposit Amount", "Net Bill Amount", "Total Payable Amount", "Outstanding Amount",
    "Bill No", "Invoice No", "GSTIN", "Patient Name", "Hospital Name", "Diagnostic Name", "Age", "Gender", "Diagnosis",
    "Date", "Doctor Name", "Referring Doctor", "Required Amount", "City", "DOB", "Patient Number", "Govt Allotted Number",
    "Address", "Phone Number", "Father's Name"
]

def clean_value(value):
    """Removes unwanted double quotes and trims whitespace."""
    if isinstance(value, str):
        return value.strip().strip('"').strip("'")
    return value

def input_image_setup(image_data):
    """Prepare image data for Gemini API."""
    return [{"mime_type": "image/png", "data": image_data}]

def get_gemini_response(image_data):
    """Calls the Gemini AI model and retrieves structured response."""
    try:
        print("📡 Sending image data to Gemini API...")
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content([INPUT_PROMPT, image_data[0], ""])
        print("✅ Received response from Gemini API.")
        return response.text.strip()
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return ""

def extract_additional_fields(text):
    """Extracts additional fields not in predefined keys from the response."""
    additional_fields = {}
    lines = text.strip().splitlines()

    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().strip('"')
            value = clean_value(value.strip().strip(","))
            value = None if value.lower() in ["null", ""] else value
            if key not in PREDEFINED_KEYS:
                additional_fields[key] = value
    return additional_fields

def assess_image_clarity(image):
    """Basic image clarity assessment using Pillow."""
    try:
        width, height = image.size
        brightness = sum(image.convert("L").getdata()) / (width * height)  # Average brightness
        clarity_feedback = "Good" if width > 500 and height > 500 and brightness > 100 else "Poor"
        return {"width": width, "height": height, "brightness": brightness, "clarity_feedback": clarity_feedback}
    except Exception:
        return {"width": 0, "height": 0, "brightness": 0, "clarity_feedback": "Error"}

def process_image(s3_key):
    """Fetch image from S3, process it, and save JSON output to S3."""
    try:
        start_time = time.time()

        print(f"📥 Fetching image: {s3_key} from S3...")
        image_obj = s3.get_object(Bucket=INPUT_BUCKET, Key=s3_key)
        image = Image.open(BytesIO(image_obj["Body"].read()))
        print(f"✅ Successfully downloaded {s3_key} from S3.")

        # ✅ Resize image for consistency
        image = image.resize((800, 800), Image.Resampling.LANCZOS)
        print("🔄 Resized image to 800x800.")

        # ✅ Convert image to bytes for Gemini API
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_data = input_image_setup(img_byte_arr.getvalue())
        print("🔹 Preparing image for Gemini API...")

        # ✅ Get AI response
        response_text = get_gemini_response(img_data)

        extracted_data = {"file_name": s3_key}
        predefined_data = {key: None for key in PREDEFINED_KEYS}
        if response_text.strip():
            lines = response_text.strip().splitlines()
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().strip('"')
                    value = clean_value(value.strip().strip(","))
                    value = None if value.lower() in ["null", ""] else value
                    if key in PREDEFINED_KEYS:
                        predefined_data[key] = value
        
        extracted_data.update(predefined_data)

        # ✅ Extract additional fields
        extracted_data.update(extract_additional_fields(response_text))

        # ✅ Assess image clarity
        extracted_data["image_clarity"] = assess_image_clarity(image)

        # ✅ Add response time
        extracted_data["response_time_seconds"] = round(time.time() - start_time, 2)

        # ✅ Store JSON output in the correct folder
        json_key = f"{OUTPUT_FOLDER}{os.path.basename(s3_key).rsplit('.', 1)[0]}.json"
        print(f"📂 Saving JSON output to S3 as {json_key}...")

        s3.put_object(Bucket=OUTPUT_BUCKET, Key=json_key, Body=json.dumps(extracted_data, indent=4))
        print(f"✅ Successfully saved JSON: {json_key}")

        return f"✅ Processed: {s3_key} → {json_key}"

    except Exception as e:
        print(f"❌ Error processing {s3_key}: {e}")
        return f"❌ Error processing {s3_key}: {e}"

def lambda_handler(event, context):
    """AWS Lambda handler function triggered by S3."""
    try:
        results = []
        for record in event["Records"]:
            s3_key = record["s3"]["object"]["key"]
            print(f"🔍 Processing new image: {s3_key}")
            results.append(process_image(s3_key))

        print("✅ All files processed successfully.")
        return {"message": "Processing complete", "results": results}

    except Exception as e:
        print(f"❌ Lambda handler error: {e}")
        return {"error": str(e)}
