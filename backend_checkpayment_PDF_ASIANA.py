from playwright.sync_api import sync_playwright
from PIL import Image, ImageOps, ImageFilter
from bs4 import BeautifulSoup
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4
import os
import io
import re
BASE_DIR = "/root/matvegoc"

# =========================
# Browser
# =========================
def create_browser(p):

    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
    )

    context = browser.new_context(

        viewport={
            "width": 2560,
            "height": 1440
        },

        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),

        locale="ko-KR"
    )

    return browser, context


# =========================
# Inject anti detect
# =========================
def inject_scripts(page):

    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });

        window.print = () => {
            console.log("Blocked print()");
        };
    """)


# =========================
# Open page
# =========================
def open_page(page, url):

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=60000
    )

    # zoom lớn cho nét
    page.evaluate("""
        document.body.style.zoom = '200%'
    """)

    page.wait_for_timeout(2000)

    element = page.locator(
        'img[alt="운임정보"]'
    )

    element.wait_for(
        state="visible",
        timeout=60000
    )

    return element


# =========================
# Extract text
# =========================
def get_page_text(page):

    html = page.content()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = soup.get_text(
        separator="\n",
        strip=True
    )

    return text


# =========================
# Extract PNR
# =========================
def extract_pnr(text):

    match = re.search(
        r"Reservation No\.\s*([A-Z0-9]{6})",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    # fallback
    match = re.search(
        r"\b[A-Z0-9]{6}\b",
        text
    )

    if match:
        return match.group(0)

    return "UNKNOWN"


# =========================
# Capture PDF
# =========================
def capture_receipt_pdf(
    page,
    element,
    pnr
):

    box = element.bounding_box()

    if not box:
        raise Exception("Không tìm thấy element")

    x = int(box["x"])
    y = int(box["y"])
    width = int(box["width"])

    # screenshot png chất lượng cao
    screenshot_bytes = page.screenshot(
        full_page=True,
        type="png"
    )

    img = Image.open(
        io.BytesIO(screenshot_bytes)
    )

    # crop đúng vùng
    cropped = img.crop(
        (x, 0, x + width, y)
    )

    # viền trắng
    bordered = ImageOps.expand(
        cropped,
        border=20,
        fill="white"
    )

    # viền xám
    bordered = ImageOps.expand(
        bordered,
        border=2,
        fill="gray"
    )

    # sharpen
    final_img = bordered.convert("RGB")

    final_img = final_img.filter(
        ImageFilter.UnsharpMask(
            radius=2,
            percent=200,
            threshold=3
        )
    )

    # save png debug
    # png_name = os.path.join(
    #     BASE_DIR,
    #     f"ASIANA-{pnr}.png"
    # )

    # final_img.save(
    #     png_name,
    #     format="PNG",
    #     optimize=True,
    #     dpi=(300, 300)
    # )

    # =========================
    # PDF
    # =========================
    pdf_name = os.path.join(
        BASE_DIR,
        f"ASIANA-{pnr}.pdf"
    )

    pdf_width, pdf_height = A4

    pdf_padding = 40

    img_width, img_height = final_img.size

    # fit ngang A4
    target_width = pdf_width - (pdf_padding * 2)

    scale_ratio = target_width / img_width

    target_height = img_height * scale_ratio

    # nếu quá cao thì fit theo chiều dọc
    max_height = pdf_height - (pdf_padding * 2)

    if target_height > max_height:

        scale_ratio = max_height / img_height

        target_width = img_width * scale_ratio
        target_height = img_height * scale_ratio

    # canh giữa
    x_position = (pdf_width - target_width) / 2
    y_position = pdf_height - target_height - pdf_padding

    c = canvas.Canvas(
        pdf_name,
        pagesize=A4
    )

    # nền trắng
    c.setFillColorRGB(1, 1, 1)

    c.rect(
        0,
        0,
        pdf_width,
        pdf_height,
        fill=1,
        stroke=0
    )

    # draw image
    c.drawImage(
        ImageReader(final_img),

        x_position,
        y_position,

        width=target_width,
        height=target_height
    )

    c.save()

    print(f"[PDF] Saved: {pdf_name}")


# =========================
# Main
# =========================
def check_payment_asiana(url):

    # url = (
    #     "https://flyasiana.com/I/kr/ko/ViewItineraryReceipt.do"
    #     "?infoData=X5L/JZBRIn5EkMfkvND8XJxidS0zGG95M8NviF7D6PuwKaSf3EpILJNAS5wdSkw9tCOu2sAdmetm/3MKUgiT+w=="
    #     "&bizType=REV"
    # )

    with sync_playwright() as p:

        browser, context = create_browser(p)

        page = context.new_page()

        inject_scripts(page)

        element = open_page(page, url)

        # =========================
        # TEXT
        # =========================
        text = get_page_text(page)

        print("\n========== PAGE TEXT ==========\n")
        # print(text)

        # =========================
        # PNR
        # =========================
        pnr = extract_pnr(text)

        print(f"\n[PNR] {pnr}")

        # =========================
        # PDF
        # =========================
        capture_receipt_pdf(
            page=page,
            element=element,
            pnr=pnr
        )

        browser.close()


# if __name__ == "__main__":
#     main()
