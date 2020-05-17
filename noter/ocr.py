import os
import pytesseract
from PIL import Image
from io import BytesIO
from PyPDF2 import PdfFileReader, PdfFileWriter
from typing import List


def concat_images_as_pdf(images: List[BytesIO]) -> BytesIO:
    output = BytesIO()
    writer = PdfFileWriter()
    input_streams = [BytesIO(pytesseract.image_to_pdf_or_hocr(
        Image.open(img), extension='pdf')) for img in images]
    for reader in map(PdfFileReader, input_streams):
        writer.addPage(reader.getPage(0))

    writer.write(output)

    return output
