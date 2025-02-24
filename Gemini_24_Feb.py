import sys
sys.path.append("/mnt/efs/python")

import os
import json
import time
import boto3
from io import BytesIO
from PIL import Image
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor

# ✅ Load API Key
API_KEY = os.getenv("Api_key1")
if not API_KEY:
    raise ValueError("❌ API Key not found!")
genai.configure(api_key=API_KEY)

# ✅ Configure AWS S3
s3 = boto3.client("s3")

# ✅ Define S3 bucket names
INPUT_BUCKET = "flask-image-api-bucket1"
OUTPUT_BUCKET = "json-extracted-output"
OUTPUT_FOLDER = "json_files/"

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

PREDEFINED_KEYS = set([
    "UHID", "IP No (Inpatient Number)", "Date of Admission (DOA)", "Date of Discharge (DOD)", "Treating Doctor",
    "Consultant", "Admission No", "Bed No", "Billing Class", "Room Type", "Pan No", "GST No", "Bill Date", "From Date",
    "To Date", "Total Bill Amount", "Deposit Amount", "Net Bill Amount", "Total Payable Amount", "Outstanding Amount",
    "Bill No", "Invoice No", "GSTIN", "Patient Name", "Hospital Name", "Diagnostic Name", "Age", "Gender", "Diagnosis",
    "Date", "Doctor Name", "Referring Doctor", "Required Amount", "City", "DOB", "Patient Number", "Govt Allotted Number",
    "Address", "Phone Number", "Father's Name"
])

def clean_value(value):
    """Removes unwanted double quotes and trims whitespace."""
    return value.strip().strip('"').strip("'") if isinstance(value, str) else value

def input_image_setup(image_bytes):
    """Prepare image data for Gemini API."""
    return [{"mime_type": "image/png", "data": image_bytes}]

def get_gemini_response(image_data):
    """Calls the Gemini AI model and retrieves structured response."""
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        return model.generate_content([INPUT_PROMPT, image_data[0], ""]).text.strip()
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return ""

def extract_fields(text):
    """Extracts predefined and additional fields from AI response."""
    extracted_data = {key: None for key in PREDEFINED_KEYS}
    additional_fields = {}
    
    for line in text.strip().splitlines():
        if ":" in line:
            key, value = map(str.strip, line.split(":", 1))
            value = clean_value(value.rstrip(","))
            value = None if value.lower() in {"null", ""} else value
            if key in PREDEFINED_KEYS:
                extracted_data[key] = value
            else:
                additional_fields[key] = value
                
    return extracted_data, additional_fields

def assess_image_clarity(image):
    """Basic image clarity assessment using Pillow."""
    try:
        width, height = image.size
        brightness = sum(image.convert("L").getdata()) / (width * height)  # Average brightness
        return {"width": width, "height": height, "brightness": brightness, 
                "clarity_feedback": "Good" if width > 500 and height > 500 and brightness > 100 else "Poor"}
    except Exception:
        return {"width": 0, "height": 0, "brightness": 0, "clarity_feedback": "Error"}

def process_image(s3_key):
    """Fetch image from S3, process it, and save JSON output to S3."""
    try:
        start_time = time.time()
        print(f"📥 Fetching: {s3_key} from S3...")
        
        image_obj = s3.get_object(Bucket=INPUT_BUCKET, Key=s3_key)
        image = Image.open(BytesIO(image_obj["Body"].read()))
        
        # ✅ Resize image only if necessary
        if image.size[0] > 800 or image.size[1] > 800:
            image.thumbnail((800, 800), Image.LANCZOS)
        
        # ✅ Convert image to bytes for Gemini API
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_data = input_image_setup(img_byte_arr.getvalue())

        # ✅ Get AI response
        response_text = get_gemini_response(img_data)

        if not response_text:
            print(f"⚠️ No response from Gemini for {s3_key}")
            return f"⚠️ No data extracted for {s3_key}"

        # ✅ Extract predefined and additional fields
        predefined_data, additional_fields = extract_fields(response_text)

        # ✅ Assess image clarity
        clarity = assess_image_clarity(image)

        # ✅ Remove keys with null values before saving
        filtered_data = {k: v for k, v in {
            "file_name": s3_key,
            "response_time_seconds": round(time.time() - start_time, 2),
            **predefined_data,
            **additional_fields,
            "image_clarity": clarity
        }.items() if v is not None}

        # ✅ Save JSON to S3
        json_key = f"{OUTPUT_FOLDER}{os.path.basename(s3_key).rsplit('.', 1)[0]}.json"
        s3.put_object(Bucket=OUTPUT_BUCKET, Key=json_key, Body=json.dumps(filtered_data, indent=4))
        
        print(f"✅ Processed: {s3_key} → {json_key}")
        return f"✅ Processed: {s3_key} → {json_key}"

    except Exception as e:
        print(f"❌ Error processing {s3_key}: {e}")
        return f"❌ Error processing {s3_key}: {e}"

def lambda_handler(event, context):
    """AWS Lambda handler function triggered by S3."""
    try:
        results = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_image, record["s3"]["object"]["key"]) for record in event["Records"]]
            for future in futures:
                results.append(future.result())

        print("✅ All files processed successfully.")
        return {"message": "Processing complete", "results": results}

    except Exception as e:
        print(f"❌ Lambda handler error: {e}")
        return {"error": str(e)}
