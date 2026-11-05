import fitz
from rapidocr_onnxruntime import RapidOCR
import os

pdf_path = r'C:\Users\Mohit Gora\.gemini\antigravity\brain\56c690af-046d-4db5-8451-fc4239b78c0b\.user_uploaded\media_1793900214686_d56df5a1.pdf'
out_txt = r'C:\Users\Mohit Gora\.gemini\antigravity\scratch\command-parser-cloud\results\assignment_ocr.txt'

engine = RapidOCR()
doc = fitz.open(pdf_path)
print(f'Total pages to OCR: {len(doc)}')

with open(out_txt, 'w', encoding='utf-8') as f_out:
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes('png')
        result, elapse = engine(img_bytes)
        f_out.write(f"\n\n=== PAGE {page_idx + 1} ===\n\n")
        if result:
            for item in result:
                # item: [box, text, score]
                f_out.write(item[1] + "\n")
        print(f"Page {page_idx + 1} done in {elapse}")

print(f"Finished OCR! Saved to {out_txt}")

