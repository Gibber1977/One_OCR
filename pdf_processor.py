import fitz  # PyMuPDF
from PIL import Image
import os
import logging
import shutil # For cleaning up test directories

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def convert_pdf_to_images(pdf_path, base_output_folder="uploads/pdf_images", dpi=300, image_format="PNG"):
    """
    将 PDF 文件的每一页转换为图像，并保存到基于 PDF 文件名的子目录中。

    参数:
        pdf_path (str): 输入 PDF 文件的路径。
        base_output_folder (str): 保存转换后图像的根文件夹路径。
                                 例如 "uploads/pdf_images"。
        dpi (int): 输出图像的分辨率 (每英寸点数)。
        image_format (str): 输出图像的格式 (例如 "PNG", "JPEG")。

    返回:
        list: 成功转换的图像文件路径列表。
              如果发生错误，则返回空列表。
    """
    image_paths = []
    if not os.path.exists(pdf_path):
        logging.error(f"PDF file not found at {pdf_path}")
        return []

    # 从 PDF 文件名创建特定的输出子文件夹
    pdf_filename_without_ext = os.path.splitext(os.path.basename(pdf_path))[0]
    specific_output_folder = os.path.join(base_output_folder, f"{pdf_filename_without_ext}_images")

    if not os.path.exists(specific_output_folder):
        try:
            os.makedirs(specific_output_folder, exist_ok=True)
            logging.info(f"Created directory: {specific_output_folder}")
        except OSError as e:
            logging.error(f"Error creating directory {specific_output_folder}: {e}")
            return []
    else:
        logging.info(f"Output directory already exists: {specific_output_folder}")


    try:
        doc = fitz.open(pdf_path)
        
        # 设置缩放矩阵以控制 DPI
        # PDF 单位是点 (1/72 英寸)。 matrix 定义了从 PDF 坐标到像素坐标的转换。
        # zoom_x = dpi / 72.0
        # zoom_y = dpi / 72.0
        # matrix = fitz.Matrix(zoom_x, zoom_y)
        # PyMuPDF 1.19.0 及更高版本可以直接在 get_pixmap 中使用 dpi 参数
        
        logging.info(f"Processing PDF: {pdf_path} with {len(doc)} pages.")

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            try:
                # 使用指定的 DPI 获取 pixmap
                pix = page.get_pixmap(dpi=dpi)
            except AttributeError: # 兼容旧版 PyMuPDF，可能没有直接的 dpi 参数
                zoom_x = dpi / 72.0
                zoom_y = dpi / 72.0
                matrix = fitz.Matrix(zoom_x, zoom_y)
                pix = page.get_pixmap(matrix=matrix)


            image_filename = f"page_{page_num + 1}.{image_format.lower()}"
            image_path = os.path.join(specific_output_folder, image_filename)
            
            try:
                # 使用 Pillow 将 Pixmap 保存为指定格式
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img.save(image_path, image_format.upper())
                image_paths.append(image_path)
                logging.info(f"Saved page {page_num + 1} to {image_path} (DPI: {dpi}, Format: {image_format.upper()})")
            except Exception as e_save:
                logging.error(f"Error saving image {image_path}: {e_save}")
                # 如果单个页面保存失败，继续处理其他页面

        doc.close()
    except fitz.fitz.FitzError as fe: # PyMuPDF 特定的错误
        logging.error(f"PyMuPDF error processing {pdf_path}: {fe}")
        return []
    except FileNotFoundError: # 这个应该在函数开始时被捕获，但为了以防万一
        logging.error(f"Error: PDF file not found at {pdf_path} (should have been caught earlier)")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred during PDF to image conversion for {pdf_path}: {str(e)}")
        return []
    
    if not image_paths:
        logging.warning(f"No images were converted from {pdf_path}.")
        
    return image_paths

if __name__ == '__main__':
    # 创建一个虚拟的测试 PDF 文件，如果它不存在
    dummy_pdf_path = "dummy_test_document.pdf"
    # 测试输出将进入 "test_output_images/dummy_test_document_images/"
    base_test_output_folder = "test_output_images" 

    try:
        if not os.path.exists(dummy_pdf_path):
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                
                c = canvas.Canvas(dummy_pdf_path, pagesize=letter)
                c.drawString(100, 750, "Page 1: Hello World from Test PDF")
                c.showPage()
                c.drawString(100, 750, "Page 2: This is a test PDF for pdf_processor.")
                c.showPage()
                c.save()
                logging.info(f"Created dummy PDF: {dummy_pdf_path}")
            except ImportError:
                logging.warning("reportlab library is not installed. Skipping dummy PDF creation.")
                logging.warning("Please install it using: pip install reportlab")
                # 如果 reportlab 不可用，则不继续测试
                exit()
            except Exception as e_create_pdf:
                logging.error(f"Could not create dummy PDF: {e_create_pdf}")
                exit()


        logging.info(f"\nConverting PDF '{dummy_pdf_path}' to images...")
        logging.info(f"Output will be in a subfolder under: '{base_test_output_folder}'")
        
        # 测试 1: 默认 DPI 和 PNG 格式
        logging.info("\n--- Test 1: Default DPI (300), PNG format ---")
        converted_images_png = convert_pdf_to_images(
            dummy_pdf_path, 
            base_output_folder=base_test_output_folder
        )

        if converted_images_png:
            logging.info("Test 1 successful. Image paths:")
            for img_path in converted_images_png:
                logging.info(f"  - {img_path}")
        else:
            logging.error("Test 1: PDF to image conversion failed or produced no PNG images.")

        # 测试 2: 指定 DPI (150) 和 JPEG 格式
        logging.info("\n--- Test 2: Custom DPI (150), JPEG format ---")
        converted_images_jpeg = convert_pdf_to_images(
            dummy_pdf_path, 
            base_output_folder=base_test_output_folder, 
            dpi=150, 
            image_format="JPEG"
        ) # JPEG 图像将覆盖同名子目录中的 PNG（如果文件名相同）
          # 但由于我们的子目录是基于 PDF 名称的，所以它们应该在同一个子目录中，但文件名不同（page_X.jpeg vs page_X.png）
          # 实际上，由于文件名是 page_X.<format>，它们不会覆盖，而是并存。

        if converted_images_jpeg:
            logging.info("Test 2 successful. Image paths:")
            for img_path in converted_images_jpeg:
                logging.info(f"  - {img_path}")
        else:
            logging.error("Test 2: PDF to image conversion failed or produced no JPEG images.")
        
        # 清理：删除 base_test_output_folder 及其所有内容
        # 首先检查文件夹是否存在并且包含预期的子文件夹
        expected_subfolder = os.path.join(base_test_output_folder, f"{os.path.splitext(os.path.basename(dummy_pdf_path))[0]}_images")
        if os.path.exists(base_test_output_folder):
            logging.info(f"\nCleaning up test output folder: {base_test_output_folder}")
            try:
                shutil.rmtree(base_test_output_folder)
                logging.info(f"Successfully removed folder and its contents: {base_test_output_folder}")
            except OSError as e:
                logging.error(f"Error removing test output folder {base_test_output_folder}: {e}")
        else:
            logging.info(f"\nTest output folder {base_test_output_folder} was not created, no cleanup needed for it.")


        # 清理虚拟 PDF (可选，可以保留用于手动检查)
        # if os.path.exists(dummy_pdf_path):
        #     os.remove(dummy_pdf_path)
        #     logging.info(f"Cleaned up dummy PDF: {dummy_pdf_path}")

    except Exception as e:
        logging.error(f"An error occurred during the test script: {e}")