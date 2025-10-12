# ocr_gemini.py
import os
import re
import json
import pathlib
from typing import Dict, Any
from dotenv import load_dotenv
load_dotenv()
import cv2
import pytesseract
from google import generativeai as genai

# ---- CẤU HÌNH ----
# GEMINI API KEY: lấy từ env
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY chưa được set trong env")

genai.configure(api_key=API_KEY)

# DÙNG model text-only để parse (không gửi ảnh)
MODEL = genai.GenerativeModel("gemini-2.0-flash")  # text model

# ---- OCR LOCAL ----
def preprocess_image_for_ocr(image_path: str) -> "numpy.ndarray":
    """
    Preprocess ảnh để tăng accuracy OCR: resize, grayscale, denoise, threshold.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Không đọc được ảnh: {image_path}")

    # resize nếu quá nhỏ/không quá lớn
    h, w = img.shape[:2]
    scale = 1.0
    if max(h, w) < 1000:
        scale = 2.0
    elif max(h, w) > 3000:
        scale = 0.7
    if scale != 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # denoise
    gray = cv2.fastNlMeansDenoising(gray, None, h=10)

    # adaptive threshold (tốt cho ảnh chụp giấy)
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 15)

    return th

def ocr_image_to_text(image_path: str, lang: str = "vie+eng") -> str:
    """
    OCR cục bộ -> trả về raw text.
    lang: 'vie' or 'eng' or 'vie+eng' tùy mong muốn.
    """
    img = preprocess_image_for_ocr(image_path)
    # config: psm 3 = fully automatic page segmentation
    config = r"--oem 3 --psm 3"
    text = pytesseract.image_to_string(img, lang=lang, config=config)

    # cleanup: normalize spaces, thay nhiều newline thành newline đơn
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text).strip()
    return text

# ---- PARSE BẰNG GEMINI (CHỈ TEXT) ----
def parse_text_with_gemini(raw_text: str) -> Dict[str, Any]:
    """
    Gửi text OCR lên Gemini (chỉ text) để nó trả JSON theo schema.
    Trả về dict JSON hoặc {'raw_response': ..., 'note': ...} nếu fail parse.
    """
    # prompt bắt buộc: bắt Gemini trả đúng JSON thuần
    prompt = (
        "Bạn là một parser chính xác. Dưới đây là văn bản OCR (có thể có lỗi chính tả do ảnh mờ).\n\n"
        "Văn bản (BEGIN):\n"
        + raw_text +
        "\n(END)\n\n"
        "Hãy tìm trong văn bản các thông tin: họ tên (không dấu, in HOA được chấp nhận), "
        "ngày tháng năm sinh, giới tính (Nam hoặc Nữ), số căn cước/cmt/định danh cá nhân (nếu có), "
        "số hộ chiếu (nếu có) và ngày hết hạn hộ chiếu (nếu có). "
        "Trả VỀ CHỈ MỘT ĐỐI TƯỢNG JSON hợp lệ (pure JSON) với các key: "
        "hoten, ngaysinh, gioitinh, cccd, sohochieu, ngayhethan. "
        "Lưu ý họ tên cần chuyển hết về dạng in hoa và không có dấu. ngaysinh và ngayhethan cần chuyển về dạng dd/mm/yyyy. gioitinh cần chuyển về dạng Nam hoặc Nu "
        "Nếu không tìm thấy trường nào thì gán giá trị null cho key đó. "
        "KHÔNG chèn giải thích, không chèn markdown, chỉ in đúng JSON thuần."
    )

    response = MODEL.generate_content([prompt])
    text = response.text.strip()

    # loại bỏ code block nếu có (phòng trường hợp)
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()

    # đôi khi model in thêm text trước/sau JSON -> tìm cái giống JSON bằng regex
    m = re.search(r"(\{[\s\S]*\})", cleaned)
    json_text = m.group(1) if m else cleaned

    try:
        data = json.loads(json_text)
        # chuẩn hoá các trường cơ bản (ví dụ: chuyển tên thành uppercase no-diacritics nếu cần)
        return data
    except json.JSONDecodeError:
        return {"raw_response": cleaned, "note": "Model không trả JSON chuẩn."}

# ---- HÀM GHÉP: OCR rồi parse ----
def ocr_then_parse(image_path: str, lang: str = "vie+eng"):
    """
    Convenience: chạy OCR cục bộ -> parse bằng Gemini -> return result dict.
    """
    if not pathlib.Path(image_path).exists():
        return {"error": "file_not_found", "msg": f"{image_path} không tồn tại"}

    raw_text = ocr_image_to_text(image_path, lang=lang)
    parsed = parse_text_with_gemini(raw_text)
    return {"text":raw_text, "parsed": parsed}
