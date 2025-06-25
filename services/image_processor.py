from pdf2image import convert_from_bytes
from io import BytesIO
from services.config import PDF_DPI

def prepare_images_sync(pdf_data):
    try:
        images = convert_from_bytes(pdf_data, dpi=PDF_DPI)
        if len(images) < 3:
            return None, None
        
        img2 = BytesIO()
        img3 = BytesIO()
        images[1].save(img2, format="JPEG")
        images[2].save(img3, format="JPEG")
        img2.seek(0)
        img3.seek(0)
        
        return img2.read(), img3.read()
    except Exception as e:
        print("Image preparation error:", e)
        return None, None