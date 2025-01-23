import fitz
from PIL import Image
import io
import os

def pdf_to_images(pdf_file, output_folder):
    pdf_document = fitz.open(pdf_file)
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        image_list = page.get_images(full=True)
        for img_index, image in enumerate(image_list):
            xref = image[0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]
            img = Image.open(io.BytesIO(image_bytes))
            pdf_name = os.path.basename(pdf_file).replace(".pdf", "")
            output_path = os.path.join(output_folder, f"{pdf_name}_page{page_num+1}_img{img_index+1}.png")
            img.save(output_path, "PNG")

def process_multiple_pdfs(input_folder, output_folder):
    pdf_files = [f for f in os.listdir(input_folder) if f.endswith(".pdf")]
    for pdf_file in pdf_files:
        pdf_path = os.path.join(input_folder, pdf_file)
        pdf_to_images(pdf_path, output_folder)

input_folder = "/Users/rahulsai/Downloads/Sample data"
output_folder = "/Users/rahulsai/Downloads/Pdf_to_PNG"
os.makedirs(output_folder, exist_ok=True)
process_multiple_pdfs(input_folder, output_folder)
