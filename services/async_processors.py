import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from services.config import MAX_WORKERS
from services.text_extractor import extract_page1_sync
from services.aws_services import extract_page2_via_textract
from services.image_processor import prepare_images_sync
from services.aws_services import compare_faces_sync

executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

async def extract_page1_data(pdf_bytes):
    start_time = time.time()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, extract_page1_sync, pdf_bytes)
    end_time = time.time()
    return result, int((end_time - start_time) * 1000)

async def extract_page2_data_via_textract(pdf_bytes):
    start_time = time.time()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, extract_page2_via_textract, pdf_bytes)
    end_time = time.time()
    return result, int((end_time - start_time) * 1000)

async def compare_faces_async(pdf_data):
    start_time = time.time()
    
    def process_faces():
        img2_bytes, img3_bytes = prepare_images_sync(pdf_data)
        if img2_bytes is None or img3_bytes is None:
            return None
        return compare_faces_sync(img2_bytes, img3_bytes)
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, process_faces)
    end_time = time.time()
    return result, int((end_time - start_time) * 1000)