from pdf2image import convert_from_bytes
from io import BytesIO
from services.config import PDF_DPI

def prepare_images_sync(pdf_data):
    try:
        images = convert_from_bytes(pdf_data, dpi=100, first_page=2, last_page=3)
        if len(images) < 2:
            return None, None

        img2 = BytesIO()
        img3 = BytesIO()

        images[0].convert("RGB").save(img2, format="JPEG", quality=75)
        images[1].convert("RGB").save(img3, format="JPEG", quality=75)

        img2.seek(0)
        img3.seek(0)

        return img2.read(), img3.read()
    except Exception as e:
        print("Image preparation error:", e)
        return None, None
