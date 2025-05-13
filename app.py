import os
from flask import Flask, request, render_template, redirect, url_for, flash, Response, send_file, jsonify
import io
import zipfile
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import logging

# 自定义模块导入
try:
    import pdf_processor
    import gemini_client
    import openai_client # 新增：导入 openai_client
except ImportError as e:
    logging.error(f"Error importing local modules: {e}")
    # 可以在这里决定是否退出或如何处理
    pdf_processor = None
    gemini_client = None
    openai_client = None # 新增：处理 openai_client 导入失败

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv()

# Flask 应用初始化
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'a_default_secret_key_for_development')
app.config['PROCESSED_DATA_CACHE'] = {} # 用于存储处理结果以供导出

# 配置
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads/pdfs')
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB 上传限制

# 确保上传文件夹存在
if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER)
        logging.info(f"Created upload folder: {UPLOAD_FOLDER}")
    except OSError as e:
        logging.error(f"Error creating upload folder {UPLOAD_FOLDER}: {e}")
        # 根据需要处理错误，例如退出应用或禁用上传功能

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    # Check if core modules are loaded. openai_client is optional depending on config.
    # We only require pdf_processor and at least one LLM client (Gemini or OpenAI/compatible)
    if not pdf_processor:
         flash('PDF 处理模块未能加载，核心功能将受影响。', 'danger')
         # We can still proceed if only PDF processing is broken, but LLM analysis won't work
         # Decide if this should block the whole app or just LLM features

    # Check if at least one LLM client is available if LLM analysis is expected
    llm_available = (gemini_client is not None) or (openai_client is not None)
    if not llm_available:
         flash('没有可用的 LLM 客户端加载。请检查服务器日志。', 'danger')
         # Decide if this should block the whole app or just LLM features

    # If core modules are missing, render index with error message
    if not pdf_processor or (not gemini_client and not openai_client):
         flash('核心处理模块未能加载，请检查服务器日志。', 'danger')
         return render_template('index.html')


    # LLM 提供商和模型选择将从表单获取，或依赖客户端的默认/环境变量

    if request.method == 'POST':
        # 从表单获取 LLM 配置
        ui_llm_provider = request.form.get('llm_provider', 'gemini').lower()
        ui_selected_model_dropdown = request.form.get('selected_model_name', '').strip() # From dropdown
        ui_custom_model_name = request.form.get('custom_model_name', '').strip() # Manual input
        ui_gemini_api_key = request.form.get('gemini_api_key', '').strip()
        ui_openai_api_key = request.form.get('openai_api_key', '').strip()
        ui_openai_base_url = request.form.get('openai_base_url', '').strip() # Added for OpenAI Base URL
        # For new OpenAI-compatible providers, we might use the same base_url field or add new ones
        # For now, let's assume the openai_base_url field is used for all OpenAI-compatible endpoints

        # Determine final model name: prioritize custom input, then dropdown
        final_model_to_use = ui_custom_model_name if ui_custom_model_name else ui_selected_model_dropdown

        # 验证提供商和客户端加载情况
        supported_providers = ['gemini', 'openai', 'volcano'] # Add new providers here

        if ui_llm_provider not in supported_providers:
             flash(f"不支持的 LLM 提供商: {ui_llm_provider}。", 'danger')
             ui_llm_provider = None # 无法处理
        elif ui_llm_provider == 'gemini' and not gemini_client:
            flash('Gemini 客户端未能加载，请检查服务器日志。', 'danger')
            ui_llm_provider = None # 无法处理
        elif ui_llm_provider in ['openai', 'volcano'] and not openai_client: # Use openai_client for openai and volcano
             flash(f'{ui_llm_provider} (OpenAI 兼容) 客户端未能加载，请检查服务器日志。', 'danger')
             ui_llm_provider = None # 无法处理

        if not ui_llm_provider:
            flash('没有可用的 LLM 客户端来处理请求。', 'danger')
            return redirect(request.url)

        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('没有文件部分', 'warning')
            return redirect(request.url)
        uploaded_files = request.files.getlist("file")
        
        if not uploaded_files or all(f.filename == '' for f in uploaded_files):
            flash('没有选择文件', 'warning')
            return redirect(request.url)

        # Get custom system prompt
        custom_system_prompt = request.form.get('custom_system_prompt', '').strip()
        default_system_prompt_from_env = os.getenv('DEFAULT_SYSTEM_PROMPT', "你是一个专业的文档分析助手。请详细分析并总结所提供图像中的内容。")
        
        final_system_prompt = custom_system_prompt if custom_system_prompt else default_system_prompt_from_env
        logging.info(f"使用的系统提示: {'自定义' if custom_system_prompt else '默认'} ({final_system_prompt[:100]}...)")
        
        all_files_results = []
        processed_one_successfully = False

        for file in uploaded_files:
            if file.filename == '':
                # Skip empty files (e.g., if user selected multiple but some were empty)
                continue

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(pdf_path)
                    logging.info(f"文件 '{filename}' 已成功保存到 '{pdf_path}'")

                    base_image_output_folder = os.path.join(os.path.dirname(app.config['UPLOAD_FOLDER']), 'pdf_images')
                    image_paths = pdf_processor.convert_pdf_to_images(
                        pdf_path=pdf_path,
                        base_output_folder=base_image_output_folder,
                        dpi=int(os.getenv('PDF_IMAGE_DPI', 300)),
                        image_format=os.getenv('PDF_IMAGE_FORMAT', 'PNG')
                    )
                    logging.info(f"PDF '{filename}' 已转换为 {len(image_paths)} 张图像。")

                    if not image_paths:
                        flash(f"PDF '{filename}' 转换为图像失败。", 'danger')
                        # Continue processing next file instead of redirecting immediately
                        all_files_results.append({
                            'original_filename': filename,
                            'error': f"PDF '{filename}' 转换为图像失败。",
                            'page_results': []
                        })
                        continue

                    current_file_page_analyses = []
                    # User prompt is now fixed as system prompt will handle instruction part
                    user_prompt_for_image = "请分析这张图片。" # Or could be removed entirely if system prompt is sufficient

                    for image_path in image_paths:
                        try:
                            logging.info(f"正在分析图像: {image_path} (来自 {filename}) 使用 LLM: {ui_llm_provider}, 模型: {final_model_to_use or '默认'}, 系统提示: {final_system_prompt[:50]}...")
                            analysis = None
                            if ui_llm_provider in ['openai', 'volcano']: # Use openai_client for openai and volcano
                                # Use the UI provided base_url for both openai and volcano
                                analysis = openai_client.analyze_image_openai(
                                    image_path=image_path,
                                    system_prompt_override=final_system_prompt,
                                    api_key_override=ui_openai_api_key or None,
                                    model_name_override=final_model_to_use or None,
                                    base_url_override=ui_openai_base_url or None # Pass the UI provided base_url
                                )
                            elif ui_llm_provider == 'gemini':
                                analysis = gemini_client.analyze_image(
                                    image_path=image_path,
                                    user_prompt=user_prompt_for_image,
                                    system_prompt_override=final_system_prompt,
                                    api_key_override=ui_gemini_api_key or None,
                                    model_name_override=final_model_to_use or None # Pass the determined model name
                                )
                            else:
                                # This case should ideally not be reached due to the provider check above
                                logging.error(f"不应发生的错误: 未知的 LLM 提供商 '{ui_llm_provider}' 在分析循环中")
                                analysis = f"错误: 未知的 LLM 提供商 '{ui_llm_provider}'"
                                
                            current_file_page_analyses.append({
                                'image_path': image_path,
                                'analysis': analysis if analysis else "未能分析此图像。"
                            })
                        except Exception as e:
                            logging.error(f"分析图像 '{image_path}' (来自 {filename}) 时出错: {e}")
                            current_file_page_analyses.append({
                                'image_path': image_path,
                                'analysis': f"分析图像时出错: {e}"
                            })
                        
                        logging.info(f"文件 '{filename}' 的所有图像分析完成。共 {len(current_file_page_analyses)} 个结果。")
                        
                        web_accessible_page_results = []
                        for res in current_file_page_analyses:
                            relative_image_path = os.path.relpath(res['image_path'], os.getcwd()).replace('\\', '/')
                        web_accessible_page_results.append({
                            'image_web_path': relative_image_path,
                            'analysis': res['analysis']
                        })
                        
                        file_data_for_template = {
                            'original_filename': filename,
                            'page_results': web_accessible_page_results
                        }
                        all_files_results.append(file_data_for_template)
                        # Store results for export (not including web accessible paths, but original analysis)
                        app.config['PROCESSED_DATA_CACHE'][filename] = {
                            'original_filename': filename,
                            'page_analyses': current_file_page_analyses # Contains original image_path and analysis
                        }
                        processed_one_successfully = True

                except pdf_processor.PDFProcessingError as e:
                    logging.error(f"PDF '{filename}' 处理错误: {e}")
                    flash(f"PDF '{filename}' 处理错误: {e}", 'danger')
                    all_files_results.append({
                        'original_filename': filename,
                        'error': f"PDF '{filename}' 处理错误: {e}",
                        'page_results': []
                    })
                except (gemini_client.GeminiClientError if gemini_client else Exception) as e: # Check if gemini_client is loaded
                    logging.error(f"Error during Gemini API call for '{filename}': {e}")
                    flash(f"处理 '{filename}' 时发生 Gemini API 错误: {e}", 'danger')
                    all_files_results.append({
                        'original_filename': filename,
                        'error': f"处理 '{filename}' 时发生 Gemini API 错误: {e}",
                        'page_results': []
                    })
                # Can add similar specific exception handling for OpenAIClientError (if defined in openai_client.py)
                # except openai_client.OpenAIClientError as e:
                #     logging.error(f"Error during OpenAI API call for '{filename}': {e}")
                #     flash(f"Error during OpenAI API call for '{filename}': {e}", 'danger')
                #     all_files_results.append({
                #         'original_filename': filename,
                #         'error': f"Error during OpenAI API call for '{filename}': {e}",
                #         'page_results': []
                #     })
                except Exception as e:
                    logging.error(f"An unknown error occurred while processing file '{filename}': {e}")
                    flash(f"处理文件 '{filename}' 时发生未知错误: {e}", 'danger')
                    all_files_results.append({
                        'original_filename': filename,
                        'error': f"处理文件 '{filename}' 时发生未知错误: {e}",
                        'page_results': []
                    })
                finally:
                    # Optional: Delete the uploaded PDF file after processing
                    # if os.path.exists(pdf_path):
                    #     try:
                    #         os.remove(pdf_path)
                    #         logging.info(f"Deleted uploaded PDF file: {pdf_path}")
                    #     except OSError as e:
                    #         logging.error(f"Error deleting PDF file {pdf_path}: {e}")
                    pass
            else:
                if file.filename: # Only show warning if filename exists
                    flash(f"File '{file.filename}' type not allowed or invalid. Please upload PDF files.", 'warning')
        
        if not processed_one_successfully and not all_files_results:
             # If no files were processed (e.g., all were invalid types or failed processing and no successful cases)
            flash('No files were successfully processed.', 'info')
            return redirect(request.url)

        return render_template('results.html', all_files_results=all_files_results)

    # GET request, load default system prompt to pre-fill textarea
    default_system_prompt = os.getenv('DEFAULT_SYSTEM_PROMPT', "你是一个专业的文档分析助手。请详细分析并总结所提供图像中的内容。")
    return render_template('index.html', default_system_prompt=default_system_prompt)


@app.route('/api/get_models/<provider>', methods=['POST']) # Changed to POST to send API key in body
def get_models(provider):
    api_key = request.json.get('api_key') if request.is_json else request.form.get('api_key')
    base_url = request.json.get('base_url') if request.is_json else request.form.get('base_url') # For OpenAI and compatible

    supported_providers = ['gemini', 'openai', 'volcano'] # Add new providers here
    if not provider or provider.lower() not in supported_providers:
        return jsonify({"error": "Invalid provider specified."}), 400

    models_data = {"error": "Provider client not loaded or failed to list models."}
    status_code = 500

    if provider.lower() == 'gemini':
        if gemini_client:
            models_data = gemini_client.list_gemini_models(api_key_override=api_key)
            status_code = 200 if "models" in models_data else (500 if "error" in models_data else 200)
        else:
            models_data = {"error": "Gemini client not loaded on server."}
            status_code = 503
            
    elif provider.lower() in ['openai', 'volcano']: # Use openai_client for openai and volcano
        if openai_client:
            # For volcano, use the specific base_url if not provided in the request
            if provider.lower() == 'volcano' and not base_url:
                 base_url = "https://ark.cn-beijing.volces.com/api/v3" # Default base_url for Volcano
                 logging.info(f"Using default base_url for Volcano: {base_url}")

            models_data = openai_client.list_openai_models(api_key_override=api_key, base_url_override=base_url)
            status_code = 200 if "models" in models_data else (500 if "error" in models_data else 200)
        else:
            models_data = {"error": f"{provider} (OpenAI compatible) client not loaded on server."}
            status_code = 503
            
    return jsonify(models_data), status_code

@app.route('/export_markdown/<original_filename>')
def export_markdown(original_filename):
    # Get processed data for this file from cache
    file_data = app.config['PROCESSED_DATA_CACHE'].get(original_filename)

    if not file_data or not file_data.get('page_analyses'):
        flash(f"Could not find analysis results for file '{original_filename}' for export.", 'warning')
        # Redirect to results page or home page might be better, or show an error page
        # Trying to find it from the last rendered results in all_files_results is unreliable
        # Temporarily redirect back to home page
        return redirect(url_for('index'))

    markdown_content = f"# Analysis Results: {file_data['original_filename']}\n\n"
    
    for i, page_data in enumerate(file_data['page_analyses']):
        markdown_content += f"## Page {i+1}\n\n"
        # Original image path: page_data['image_path'] - can optionally include
        # markdown_content += f"![Page Image]({page_data['image_path']})\n\n" # Local path may not display in all MD viewers
        markdown_content += f"**Analysis Text:**\n```\n{page_data['analysis']}\n```\n\n"
        markdown_content += "---\n\n"

    # Create Markdown file for download
    response = Response(
        markdown_content,
        mimetype="text/markdown",
        headers={"Content-disposition": f"attachment; filename={original_filename}_analysis.md"}
    )
    return response

@app.route('/export_all_markdown_zip')
def export_all_markdown_zip():
    processed_data = app.config.get('PROCESSED_DATA_CACHE')
    if not processed_data:
        flash('No processed files available for export.', 'warning')
        return redirect(url_for('index'))

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for original_filename, file_data in processed_data.items():
            if not file_data or not file_data.get('page_analyses'):
                logging.warning(f"Skipping file '{original_filename}' as its analysis data was not found during batch export.")
                continue

            markdown_content = f"# Analysis Results: {file_data['original_filename']}\n\n"
            for i, page_data in enumerate(file_data['page_analyses']):
                markdown_content += f"## Page {i+1}\n\n"
                markdown_content += f"**Analysis Text:**\n```\n{page_data['analysis']}\n```\n\n"
                markdown_content += "---\n\n"
            
            # Create .md file using original filename
            markdown_filename = f"{original_filename}_analysis.md"
            zf.writestr(markdown_filename, markdown_content)
            logging.info(f"Added '{markdown_filename}' to ZIP file.")

    memory_file.seek(0)
    
    if not memory_file.getvalue(): # Check if ZIP file is empty
        flash('Failed to generate any Markdown files into the ZIP package.', 'danger')
        return redirect(url_for('results')) # or index

    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='all_markdown_exports.zip'
    )

# Add a route to serve uploaded images
# This is necessary to display images in results.html
@app.route('/uploads_img/<path:filepath>')
def uploaded_file_image(filepath):
    # filepath will be something like 'pdf_images/filename_images/page_1.png'
    # We need to serve it from the project root (or a known parent directory)
    # The parent directory of UPLOAD_FOLDER ('uploads/pdfs') is 'uploads'
    # base_image_output_folder is 'uploads/pdf_images'
    # So, we should build the path starting from the 'uploads' directory
    # For security, should restrict which paths can be accessed
    # image_directory = os.path.join(os.path.dirname(app.config['UPLOAD_FOLDER']), 'pdf_images')
    # secure_path = safe_join(image_directory, filepath) # safe_join needs import
    # return send_from_directory(os.path.dirname(secure_path), os.path.basename(secure_path))

    # Simpler (but not fully secure) approach:
    # Assume filepath is already the correct path relative to the 'uploads' directory
    # E.g., if filepath is 'pdf_images/my_doc_images/page_1.png'
    # Then the full path is 'uploads/pdf_images/my_doc_images/page_1.png'
    from flask import send_from_directory
    # The 'uploads' directory is the parent of UPLOAD_FOLDER ('uploads/pdfs')
    uploads_base_dir = os.path.dirname(app.config['UPLOAD_FOLDER']) # 'uploads'
    # Ensure path is safe to prevent directory traversal attacks
    # os.path.normpath cleans up paths like '..'
    # secure_filepath = secure_filename(filepath) # secure_filename is mainly for filenames, not paths
    # We need to ensure filepath does not contain '..' etc.
    # A safer approach would be to use safe_join (werkzeug.security.safe_join)
    # Or explicitly serve files from a known, trusted root directory
    # image_full_path = os.path.join(uploads_base_dir, filepath)
    # if not os.path.abspath(image_full_path).startswith(os.path.abspath(uploads_base_dir)):
    #     return "Forbidden", 403
    # return send_from_directory(os.path.dirname(image_full_path), os.path.basename(image_full_path))

    # Assuming filepath is already the correct path relative to the 'uploads' directory, e.g., 'pdf_images/...'
    # and that pdf_processor generates paths this way
    # In web_accessible_results, relative_image_path is 'uploads/pdf_images/...'
    # So, when the template requests /uploads_img/uploads/pdf_images/... we need to strip the leading 'uploads/'
    if filepath.startswith('uploads/'):
        filepath = filepath[len('uploads/'):]

    # send_from_directory's first argument is the directory, second is the filename
    # We need to serve 'pdf_images/...' from the 'uploads' directory
    # So, the directory is 'uploads', and the filename is 'pdf_images/...'
    # Or, the directory is 'uploads/pdf_images', and the filename is 'filename_images/page_1.png'
    # Let's assume filepath is 'pdf_images/filename_images/page_1.png'
    # Then we serve it from the 'uploads' directory
    logging.info(f"Attempting to serve file: directory='{uploads_base_dir}', filepath='{filepath}'")
    try:
        return send_from_directory(uploads_base_dir, filepath)
    except Exception as e:
        logging.error(f"Error serving file {filepath}: {e}")
        return "File not found", 404


if __name__ == '__main__':
    if not app.secret_key or app.secret_key == 'a_default_secret_key_for_development':
        logging.warning("警告: 正在使用默认或空的 FLASK_SECRET_KEY。请在 .env 文件中设置一个强密钥用于生产环境。")
    
    # Check module loading status on startup
    loaded_modules = []
    if pdf_processor: loaded_modules.append("pdf_processor")
    if gemini_client: loaded_modules.append("gemini_client")
    if openai_client: loaded_modules.append("openai_client")
    logging.info(f"已加载模块: {', '.join(loaded_modules) if loaded_modules else '无'}")

    if not pdf_processor:
        logging.error("错误: pdf_processor 未能加载。核心功能将受影响。")
    
    # Check LLM clients based on configuration
    llm_provider_on_startup = os.getenv('LLM_PROVIDER', 'gemini').lower()
    if llm_provider_on_startup == 'gemini' and not gemini_client:
        logging.error("错误: 配置使用 Gemini，但 gemini_client 未能加载。")
    elif llm_provider_on_startup in ['openai', 'volcano'] and not openai_client: # Check for openai_client for openai and volcano
        logging.error(f"错误: 配置使用 {llm_provider_on_startup}，但 {llm_provider_on_startup} (OpenAI 兼容) 客户端未能加载。")
    elif llm_provider_on_startup not in ['gemini', 'openai', 'volcano']: # Add new providers here
        logging.warning(f"警告: .env 文件中的 LLM_PROVIDER ('{llm_provider_on_startup}') 不是支持的提供商。将默认为 'gemini'。")

    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('FLASK_RUN_PORT', 5000)))