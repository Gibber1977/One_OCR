# Decision Log

This file records architectural and implementation decisions using a list format.
2025-05-13 19:11:35 - Log of updates made.

*

## Decision

*   [2025-05-13 19:11:35] - 选择 Python 和 Flask 作为 Web 应用程序的后端技术栈。
*   [2025-05-13 19:11:35] - 选择 Google Gemini API 进行 PDF 内容分析和 OCR。
*   [2025-05-13 19:11:35] - 采用模块化设计，将 PDF 处理、Gemini API 交互和 Flask 应用逻辑分离到不同的 Python 文件中。
*   [2025-05-13 19:11:35] - 使用环境变量管理 API 密钥以增强安全性。

## Rationale

*   Flask 是一个轻量级且灵活的 Python Web 框架，适合快速开发此类应用。Python 拥有丰富的库支持 PDF 处理和 API 集成。
*   Google Gemini API 提供了强大的内容分析和 OCR 功能。
*   模块化设计提高了代码的可维护性、可测试性和可重用性。
*   环境变量是存储敏感信息（如 API 密钥）的标准且安全的方法。

## Implementation Details

*   Flask 主应用: `app.py`
*   PDF 处理: `pdf_processor.py`
*   Gemini API 客户端: `gemini_client.py`
*   Web 模板: `templates/index.html`, `templates/results.html`
*   API 密钥存储: `.env` 文件 (通过 `python-dotenv` 库加载)
*   依赖管理: `requirements.txt`
---
### Decision (Code)
[2025-05-13 19:34:37] - 解决 `gemini_client.py` 中 Gemini API 调用挂起问题

**Rationale:**
观察到 API 调用长时间无响应。为了提高健壮性和可调试性，进行了以下更改：
1.  **超时设置:** 为 `model.generate_content` 调用添加了 60 秒的超时，以防止无限期挂起。
2.  **模型更改:** 将模型从 `'gemini-2.0-flash'` 更改为 `'gemini-1.5-flash-latest'`，后者可能更稳定或具有更好的性能特征。
3.  **增强的错误处理:** 添加了对特定 Google API 错误（如 `DeadlineExceeded`）、PIL 图像错误 (`UnidentifiedImageError`) 和其他潜在异常的捕获。
4.  **详细日志记录:** 集成了 Python `logging` 模块，替换了原有的 `print` 语句，以便更好地跟踪执行流程和调试问题。
5.  **图像加载:** 显式调用 `img.load()` 以确保 PIL 图像数据完全加载。
6.  **响应解析:** 改进了从 API 响应中提取文本的逻辑，使其能够处理更多边缘情况和不同的响应结构。

**Details:**
修改了 [`gemini_client.py`](gemini_client.py:1) 中的 [`analyze_image`](gemini_client.py:23) 函数。
---
### Decision (Code)
[2025-05-13 19:40:36] - 添加纯文本 API 调用测试以诊断 `gemini_client.py` 中的持续挂起问题

**Rationale:**
尽管之前尝试通过添加超时、更改模型和增强错误处理来解决 API 调用挂起问题，但问题仍然存在。为了进一步缩小问题范围，决定添加一个独立的纯文本生成测试函数 (`test_text_generation`)。此函数使用 `gemini-pro` 模型（一个标准的文本模型）进行简单的文本生成请求。

此举的目的是：
1.  **隔离问题**: 判断挂起问题是否特定于多模态（图像）API 调用，还是一个更普遍的与 Gemini API 的连接或认证问题。
2.  **简化测试**: 纯文本调用通常比图像调用涉及的变量更少，更容易诊断。

**Details:**
1.  在 [`gemini_client.py`](gemini_client.py:1) 中创建了新的函数 `test_text_generation()` ([`gemini_client.py:29`](gemini_client.py:29) 在更新后的文件中)。
2.  修改了 `if __name__ == '__main__':` ([`gemini_client.py:170`](gemini_client.py:170) 在更新后的文件中) 测试块，使其首先执行 `test_text_generation()` ([`gemini_client.py:29`](gemini_client.py:29) 在更新后的文件中)，然后再尝试图像分析测试。
---
### Decision (Code)
[2025-05-13 19:42:47] - 修改 `gemini_client.py` 以支持通过环境变量配置网络代理

**Rationale:**
用户反馈即使在之前的修改（超时、模型更改、增强错误处理、纯文本测试）之后，API 调用仍然挂起，并且确认他们正在使用网络代理。网络代理是导致出站 HTTP/HTTPS 请求（如对 Gemini API 的请求）失败或挂起的常见原因，如果客户端库没有正确配置为使用该代理。

标准 Python HTTP 客户端库（如 `requests` 和 `httpx`，`google-generativeai` 可能依赖这些库）会自动检测并使用 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量。

因此，决定采取以下措施：
1.  修改 [`gemini_client.py`](gemini_client.py:1) 以在脚本启动时从 `.env` 文件（通过 `python-dotenv`）加载这些环境变量。
2.  记录检测到的代理设置，以便用户可以验证它们是否被正确加载。
3.  提供明确的指示，告知用户如何在他们的 `.env` 文件中设置这些代理变量。

**Details:**
1.  在 [`gemini_client.py`](gemini_client.py:1) 的开头添加了代码，用于通过 `os.getenv()` ([`gemini_client.py:12`](gemini_client.py:12) 在更新后的文件中) 读取 `HTTP_PROXY` 和 `HTTPS_PROXY`。
2.  添加了日志语句，用于在检测到这些变量时打印其值 ([`gemini_client.py:15`](gemini_client.py:15) 和 [`gemini_client.py:18`](gemini_client.py:18) 在更新后的文件中)。
3.  在日志中添加了关于如何在 `.env` 文件中设置代理的示例说明 ([`gemini_client.py:23`](gemini_client.py:23) 在更新后的文件中)。
---
### Decision (Code)
[2025-05-13 19:45:46] - 修正 `gemini_client.py` 中 `test_text_generation` 函数的文本模型名称

**Rationale:**
在通过配置网络代理解决了主要的 API 调用挂起问题后，运行脚本的日志显示 `test_text_generation` 函数因找不到模型 `gemini-pro` (API 版本 v1beta) 而失败 (404错误)。图像分析部分（使用 `gemini-1.5-flash-latest`）则成功运行。

为了确保纯文本测试功能也能正常工作，需要将其模型更改为一个已知有效的文本生成模型。

**Details:**
1.  在 [`gemini_client.py`](gemini_client.py:1) 的 `test_text_generation` ([`gemini_client.py:56`](gemini_client.py:56)) 函数中，将 `text_model_name` 从 `'gemini-pro'` 修改为 `'gemini-1.0-pro'` ([`gemini_client.py:62`](gemini_client.py:62))。 `'gemini-1.0-pro'` 是一个广泛可用且支持 `generateContent` 方法的文本模型。
---
### Decision (Code)
[2025-05-13 19:47:33] - 暂时注释掉 `gemini_client.py` 中的 `test_text_generation()` 调用

**Rationale:**
尽管尝试了不同的文本模型（`gemini-pro`，然后是 `gemini-1.0-pro`），`test_text_generation()` ([`gemini_client.py:56`](gemini_client.py:56)) 函数仍然因模型不可用而失败。核心的图像分析功能（使用 `gemini-1.5-flash-latest` ([`gemini_client.py:100`](gemini_client.py:100))) 在配置了正确的代理设置后已确认可以正常工作。

由于 `test_text_generation()` ([`gemini_client.py:56`](gemini_client.py:56)) 的主要目的是帮助诊断连接问题（现已解决），并且持续的文本模型错误可能会让用户感到困惑，因此决定暂时将其从主执行路径中移除。

**Details:**
1.  在 [`gemini_client.py`](gemini_client.py:1) 的 `if __name__ == '__main__':` ([`gemini_client.py:170`](gemini_client.py:170)) 测试块中，对 `test_text_generation()` ([`gemini_client.py:56`](gemini_client.py:56)) 的调用及其相关的日志记录语句已被注释掉 ([`gemini_client.py:183`](gemini_client.py:183) 在更新后的文件中)。
2.  添加了注释，说明如果将来需要纯文本生成测试，应取消注释这些行，并使用 `client.list_models()` 查找当前可用的有效文本模型。
---
### Decision (Code)
[2025-05-13 19:50:00] - 实现 Gemini API 模型的灵活配置

**Rationale:**
根据用户反馈，需要能够灵活选择用于图像分析和文本生成的 Gemini 模型。通过环境变量配置模型名称，可以方便地切换模型（例如，`gemini-1.5-flash-latest`, `gemini-1.5-pro-latest` 等），而无需修改代码。这也为未来支持自定义模型源或不同提供商的模型奠定了基础。

**Details:**
1.  在 [`gemini_client.py`](gemini_client.py:1) 中：
    *   添加了从环境变量 `GEMINI_VISION_MODEL` (默认: `"gemini-1.5-flash-latest"`) 和 `GEMINI_TEXT_MODEL` (默认: `"gemini-1.0-pro"`) 加载模型名称的逻辑。
    *   `analyze_image` ([`gemini_client.py:97`](gemini_client.py:97)) 函数现在使用 `GEMINI_VISION_MODEL`。
    *   `test_text_generation()` ([`gemini_client.py:62`](gemini_client.py:62)) 函数现在使用 `GEMINI_TEXT_MODEL` (尽管该函数的调用在主测试脚本中仍被注释)。
2.  在 [`.env.example`](.env.example:1) 文件中添加了 `GEMINI_VISION_MODEL` 和 `GEMINI_TEXT_MODEL` 的示例条目。
3.  未来的增强可能包括支持从其他模型提供商（如 OpenAI）加载模型，这可以记录为一个潜在的未来功能。
---
### Decision (Code)
[2025-05-13 19:53:48] - 实现 PDF 处理模块 (`pdf_processor.py`)

**Rationale:**
根据项目需求，需要一个模块将上传的 PDF 文件转换为图像，以便后续进行内容分析。
1.  **库选择:** 使用 `PyMuPDF` (fitz) 进行 PDF 解析和页面到 pixmap 的转换，因为它性能良好且功能强大。使用 `Pillow` (PIL) 将 pixmap 保存为常见的图像格式 (PNG, JPEG)。这些库已在 [`requirements.txt`](requirements.txt:1) 中。
2.  **输出结构:** 为了更好地组织生成的图像并避免文件名冲突，决定为每个处理的 PDF 文件创建一个唯一的子目录。子目录名称基于原始 PDF 文件名，例如 `uploads/pdf_images/YOUR_PDF_FILENAME_images/page_1.png`。
3.  **可配置性:** 增加了通过函数参数配置输出图像 DPI (默认为 300) 和图像格式 (默认为 "PNG") 的功能，以提供灵活性。
4.  **错误处理与日志记录:** 集成了 Python 的 `logging` 模块以提供更清晰的执行跟踪和错误报告。实现了对文件未找到、目录创建失败以及 PDF 处理过程中可能发生的其他异常的处理。
5.  **兼容性:** 在 `get_pixmap` 调用中添加了对旧版 `PyMuPDF` 的兼容性处理，以防 `dpi` 参数不可用。

**Details:**
1.  修改了 [`pdf_processor.py`](pdf_processor.py:1) 中的 `convert_pdf_to_images` ([`pdf_processor.py:7`](pdf_processor.py:7)) 函数。
    *   输入参数包括 `pdf_path`, `base_output_folder`, `dpi`, `image_format`。
    *   输出图像保存在 `base_output_folder` 下的 `{pdf_filename_without_ext}_images` 子目录中。
    *   使用 `os.makedirs(exist_ok=True)` 创建输出目录。
    *   使用 `page.get_pixmap(dpi=dpi)` (或带 `matrix` 的回退方案) 和 `Image.frombytes().save()` 进行转换和保存。
2.  更新了 [`pdf_processor.py`](pdf_processor.py:1) 中的 `if __name__ == '__main__':` ([`pdf_processor.py:97`](pdf_processor.py:97)) 测试块，以验证新功能，包括不同的 DPI 和图像格式，并使用 `shutil.rmtree` 清理测试生成的目录。
---
### Decision (Code)
[2025-05-13 19:56:56] - 实现 Flask Web 应用 ([`app.py`](app.py:1)) 及前端模板 ([`templates/index.html`](templates/index.html:1), [`templates/results.html`](templates/results.html:1))

**Rationale:**
根据项目需求，需要一个 Web 界面来允许用户上传 PDF 文件，并查看由 `pdf_processor.py` 和 `gemini_client.py` 处理后的分析结果。
1.  **Flask 应用 ([`app.py`](app.py:1)):**
    *   使用 Flask 作为 Web 框架，因为它轻量级且易于上手。
    *   实现了主路由 (`/` 或 `/index`)，支持 `GET` (显示上传表单) 和 `POST` (处理文件上传和分析) 请求。
    *   配置了上传文件夹 (`uploads/pdfs`)，并确保其在应用启动时存在。
    *   实现了文件类型验证 (仅 PDF) 和大小限制。
    *   在 `POST` 请求中，按顺序调用 `pdf_processor.convert_pdf_to_images()` 和 `gemini_client.analyze_image()`。
    *   使用 Flask 的 `flash` 消息进行用户反馈。
    *   从 `.env` 文件加载配置 (如 `FLASK_SECRET_KEY`, `UPLOAD_FOLDER`)。
    *   添加了一个专门的路由 (`/uploads_img/<path:filepath>`) 来安全地提供由 `pdf_processor` 生成的图像，以便在结果页面上显示。这是必要的，因为这些图像存储在非标准的静态文件夹位置。
2.  **HTML 模板:**
    *   [`templates/index.html`](templates/index.html:1): 包含一个标准的 HTML 文件上传表单，使用了 Bootstrap 进行基本样式化。包含 `enctype="multipart/form-data"`。
    *   [`templates/results.html`](templates/results.html:1): 遍历分析结果，为每个原始 PDF 页面/图像及其对应的文本结果创建一个条目。使用 `url_for('uploaded_file_image', ...)` 来引用图像。提供返回主页的链接。使用了 Bootstrap 进行样式化。
3.  **集成:**
    *   确保 [`app.py`](app.py:1) 正确导入并使用 `pdf_processor` 和 `gemini_client` 模块。
    *   错误处理：在文件处理、PDF 转换和 Gemini API 调用过程中添加了基本的 `try-except` 块，并通过 `flash` 消息向用户报告错误。

**Details:**
*   **Flask 应用:** [`app.py`](app.py:1) (包含路由、文件处理、模块调用逻辑)
*   **上传表单:** [`templates/index.html`](templates/index.html:1)
*   **结果显示:** [`templates/results.html`](templates/results.html:1)
*   **图像服务路由:** 在 [`app.py`](app.py:1) 中定义了 `uploaded_file_image(filepath)` 路由。
*   **配置:** 依赖 `.env` 文件中的 `FLASK_SECRET_KEY`, `UPLOAD_FOLDER`, `PDF_IMAGE_DPI`, `PDF_IMAGE_FORMAT`, `GEMINI_USER_PROMPT`。
---
### Decision (Code)
[2025-05-13 20:02:55] - 实现批量 PDF 上传和 Markdown 导出功能

**Rationale:**
根据用户反馈，需要增强应用程序以支持一次处理多个 PDF 文件，并能将单个文件的分析结果导出为 Markdown 格式。

1.  **批量上传:**
    *   **目标:** 允许用户在一次操作中选择并上传多个 PDF 文件进行分析。
    *   **前端 ([`templates/index.html`](templates/index.html:1)):**
        *   修改文件输入字段 (`<input type="file">`)，添加 `multiple` 属性。
        *   更新 JavaScript 以正确显示多个选定文件的信息（例如，“X 个文件已选择”）。
    *   **后端 ([`app.py`](app.py:1)):**
        *   在 `index` 路由中，使用 `request.files.getlist("file")` 来接收所有上传的文件。
        *   迭代处理每个文件：保存、调用 `pdf_processor`、调用 `gemini_client`。
        *   聚合所有已处理文件的结果。
        *   修改传递给 [`templates/results.html`](templates/results.html:1) 的数据结构，使其成为一个包含每个文件结果的列表（每个列表项包含文件名和该文件的页面分析）。
    *   **结果显示 ([`templates/results.html`](templates/results.html:1)):**
        *   修改模板以迭代处理新的聚合结果数据结构。
        *   为每个上传的文件创建一个单独的显示区域，包括其文件名和逐页分析。

2.  **Markdown 导出:**
    *   **目标:** 为每个成功分析的 PDF 文件提供一个选项，将其分析结果下载为 Markdown 文件。
    *   **结果缓存 ([`app.py`](app.py:1)):**
        *   在 Flask 应用配置中引入一个简单的内存缓存 (`app.config['PROCESSED_DATA_CACHE'] = {}`)。
        *   在 `index` 路由成功处理完一个文件后，将其原始分析结果（文件名、页面图像路径、页面分析文本）存储到此缓存中，以原始文件名作为键。这避免了为导出重新处理文件的需要。
        *   *注意: 这是一个简化的缓存方案，适用于单用户或开发环境。对于生产环境，可能需要更健壮的缓存机制（如 Redis, Memcached 或基于文件的缓存）。*
    *   **导出路由 ([`app.py`](app.py:1)):**
        *   创建新路由 `@app.route('/export_markdown/<original_filename>')`。
        *   该路由从 `PROCESSED_DATA_CACHE` 中检索指定 `original_filename` 的分析数据。
        *   如果数据不存在，则向用户显示错误或重定向。
        *   将检索到的数据格式化为 Markdown 字符串：
            *   主标题为文件名。
            *   每个页面一个子部分，包含其分析文本。图像本身不直接嵌入 Markdown，但可以考虑包含图像路径的引用。
        *   使用 `flask.Response` 对象将 Markdown 内容作为文件附件（`.md` 文件）发送给用户，并设置正确的 MIME 类型 (`text/markdown`) 和 `Content-Disposition` 头部。
    *   **前端触发 ([`templates/results.html`](templates/results.html:1)):**
        *   在每个成功处理的文件的结果显示区域，添加一个“导出为 Markdown”的按钮/链接。
        *   此链接指向新创建的导出路由，并将相应的文件名作为参数传递。

**Details:**
*   **批量上传修改:**
    *   [`templates/index.html`](templates/index.html:1): `input` 标签添加 `multiple`，更新 JS。
    *   [`app.py`](app.py:1): `index` 路由修改为循环处理 `request.files.getlist("file")`，聚合结果。
    *   [`templates/results.html`](templates/results.html:1): 更新 Jinja 循环以显示多个文件的结果。
*   **Markdown 导出实现:**
    *   [`app.py`](app.py:1): 添加 `PROCESSED_DATA_CACHE`，在 `index` 路由中填充缓存，添加 `/export_markdown/<original_filename>` 路由。
    *   [`templates/results.html`](templates/results.html:1): 为每个文件结果添加导出按钮链接到新路由。
---
### Decision (Debug)
[2025-05-13 20:10:17] - [Bug Fix Strategy: Import `Response` in `app.py`]

**Rationale:**
The `NameError: name 'Response' is not defined` in the `export_markdown` function of [`app.py`](app.py:208) was caused by the `Response` object not being imported from Flask. Adding `Response` to the import statement `from flask import ...` resolves this.

**Details:**
Modified [`app.py`](app.py:1) to change the import from `from flask import Flask, request, render_template, redirect, url_for, flash` to `from flask import Flask, request, render_template, redirect, url_for, flash, Response`.
---
### Decision (Code)
[2025-05-13 20:12:49] - 实现批量导出 Markdown 为 ZIP 压缩包功能

**Rationale:**
用户反馈希望能够批量导出所有已处理 PDF 的 Markdown 分析结果，而不仅仅是单个文件导出。这将提高用户处理多个文件时的效率。
1.  **后端实现 ([`app.py`](app.py:1)):**
    *   创建新的 Flask 路由 `/export_all_markdown_zip`。
    *   该路由从 `app.config['PROCESSED_DATA_CACHE']` 获取所有已处理文件的数据。
    *   使用 Python 的 `zipfile` 和 `io` 模块在内存中创建一个 ZIP 文件。
    *   为缓存中的每个文件生成其 Markdown 内容（复用现有 `export_markdown` 函数的部分逻辑，主要是 Markdown 格式化部分）。
    *   将每个 Markdown 内容作为单独的文件（例如，`original_filename_analysis.md`）添加到 ZIP 包中。
    *   返回一个 Flask `send_file` 响应，将 ZIP 文件作为附件提供给用户下载，MIME 类型为 `application/zip`。
    *   添加了对缓存为空或生成 ZIP 失败的错误处理。
2.  **前端实现 ([`templates/results.html`](templates/results.html:1)):**
    *   在结果页面的顶部（如果存在结果）添加了一个“全部导出为 Markdown (ZIP)”按钮。
    *   该按钮链接到新的 `/export_all_markdown_zip` 路由。
    *   按钮使用了 Bootstrap 图标以提高用户体验。
3.  **依赖项:**
    *   `zipfile` 和 `io` 是 Python 标准库的一部分，无需额外添加依赖。
    *   `send_file` 从 `flask` 导入。

**Details:**
*   修改了 [`app.py`](app.py:1) 以添加新的路由 `export_all_markdown_zip()` ([`app.py:215`](app.py:215)) 和必要的导入 (`io`, `zipfile`, `send_file` from `flask`).
*   修改了 [`templates/results.html`](templates/results.html:1) 以在结果列表上方添加新的导出按钮 ([`templates/results.html:53`](templates/results.html:53)).
---
### Decision (Code)
[2025-05-13 20:15:00] - 实现 Flask 应用端口的可配置性

**Rationale:**
允许用户通过环境变量 `FLASK_RUN_PORT` 自定义应用程序的运行端口，提高了灵活性和部署便利性。如果未设置环境变量，则回退到默认端口 5000。

**Details:**
*   修改了 [`app.py`](app.py:1) 中的 `app.run()` ([`app.py:313`](app.py:313)) 调用，以从 `os.getenv('FLASK_RUN_PORT', 5000)` 读取端口。
*   更新了 [`.env.example`](.env.example:1) 以包含 `FLASK_RUN_PORT=5000` 作为示例。
*   更新了 [`README.md`](README.md:1) 的“运行应用程序”部分，说明了如何配置此环境变量。
*   对于外部 API（如 Gemini）的端口，通常由服务本身决定，客户端通过标准 HTTPS (443) 访问。如果通过代理，则代理 URL 中应包含端口。如果用户有更具体的自托管模型端口需求，未来可以进一步探讨。
---
### Decision
[2025-05-13 20:34:00] - 实现用户可自定义的系统提示功能。

**Rationale:**
允许用户提供自定义系统提示，可以更灵活地指导 LLM 的内容分析行为，从而针对不同类型的 PDF 或分析目标获得更精确或定制化的结果。这增强了应用程序的通用性和用户控制能力。

**Implications/Details:**
*   **UI ([`templates/index.html`](templates/index.html:1)):** 需要添加一个 `<textarea>` 供用户输入系统提示。
*   **Backend ([`app.py`](app.py:1)):** `index` 路由需要从表单接收此提示，并将其传递给 LLM 客户端。如果用户未提供提示，则可以使用默认提示或不传递该参数。
*   **LLM Client ([`gemini_client.py`](gemini_client.py:1) 和未来的 `openai_client.py`):** 客户端中的分析函数（例如 `analyze_image`）需要修改以接受一个可选的 `system_prompt` 参数，并将其包含在发送给相应 LLM API 的请求中。

---
### Decision
[2025-05-13 20:34:00] - 引入对多种 LLM 提供商的支持（首先是 OpenAI 作为 Gemini 的备选项）。

**Rationale:**
支持多种 LLM 提供商为用户提供了选择，可以根据成本、性能、特定功能或个人偏好选择最适合的 LLM。这也降低了对单一提供商的依赖性，并为未来集成更多 LLM 提供了框架。

**Implications/Details:**
*   **Configuration ([`.env`](.env:1)):** 需要添加新的环境变量来管理不同提供商的 API 密钥、模型名称等 (例如 `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL_NAME`)。
*   **New Module (`openai_client.py`):** 需要创建一个新的 Python 模块，该模块封装与 OpenAI API 的交互逻辑。此模块应提供与现有 [`gemini_client.py`](gemini_client.py:1) 类似的核心功能接口（例如，一个接受图像数据和可选系统提示并返回分析文本的函数）。
*   **Dispatcher Logic ([`app.py`](app.py:1)):** [`app.py`](app.py:1) 中需要实现一个分发机制或工厂，根据环境变量 `LLM_PROVIDER` 的值来动态选择和初始化正确的 LLM 客户端（Gemini 或 OpenAI）。
*   **Interface Consistency:** 为简化 [`app.py`](app.py:1) 中的调用逻辑，`gemini_client.py` 和 `openai_client.py` 中的核心分析函数应遵循一致的参数签名和返回类型。
*   **Dependencies ([`requirements.txt`](requirements.txt:1)):** 需要将 `openai` Python 库添加到项目依赖中。
*   **System Pattern:** 此更改引入了“LLM 提供商抽象/策略模式”，已在 [`memory-bank/systemPatterns.md`](memory-bank/systemPatterns.md:1) 中记录。
---
### Decision (Code)
[2025-05-13 20:36:00] - 实现用户可自定义系统提示功能

**Rationale:**
允许用户通过 Web 界面提供自定义系统提示，以替代从 `.env` 文件加载的 `DEFAULT_SYSTEM_PROMPT`。这增强了用户对 LLM 分析过程的控制，允许更灵活和针对性的内容分析。

**Details:**
*   **UI 变更 ([`templates/index.html`](templates/index.html:1)):**
    *   在文件上传表单中添加了一个 `<textarea name="custom_system_prompt">`。
    *   此文本区域预填充了从后端传递的当前默认系统提示 (`default_system_prompt` 变量)。
*   **后端逻辑 ([`app.py`](app.py:1)):**
    *   修改了 `/` (或 `/index`) 路由的 `GET` 请求处理：
        *   从环境变量 `DEFAULT_SYSTEM_PROMPT` (如果存在) 或一个硬编码的默认值加载默认系统提示。
        *   将此默认提示传递给 [`templates/index.html`](templates/index.html:1) 作为 `default_system_prompt`。
    *   修改了 `/upload` (或 `/index` 的 `POST` 处理) 路由：
        *   从 `request.form` 中获取 `custom_system_prompt` 的值。
        *   如果用户提供了自定义提示 (非空且去除首尾空格后非空)，则使用该提示。
        *   否则，回退到从环境变量 `DEFAULT_SYSTEM_PROMPT` 加载的提示。
        *   将最终确定的系统提示 (`final_system_prompt`) 传递给 `gemini_client.analyze_image` ([`gemini_client.py:104`](gemini_client.py:104)) 函数的 `system_prompt_override` 参数。
*   **LLM 客户端模块 ([`gemini_client.py`](gemini_client.py:1)):**
    *   修改了 `analyze_image` ([`gemini_client.py:104`](gemini_client.py:104)) 函数，使其接受一个新的可选参数 `system_prompt_override=None`。
    *   在函数内部，如果 `system_prompt_override` 被提供且非空，则使用它作为最终的系统提示。否则，使用模块级别的 `DEFAULT_SYSTEM_PROMPT`。
    *   更新了 `GenerativeModel` 的实例化，使用 `system_instruction=final_system_prompt` 参数来传递系统提示。
    *   `analyze_images_batch` ([`gemini_client.py:166`](gemini_client.py:166)) 函数也更新以传递 `system_prompt_override`。
*   **环境变量:**
    *   利用现有的 `DEFAULT_SYSTEM_PROMPT` 环境变量作为回退和在 UI 中预填充的值。
---
### Decision (Code)
[2025-05-13 20:39:09] - 实现对 OpenAI API 的支持作为备选 LLM 提供商

**Rationale:**
为了提供更大的灵活性，允许用户在 Gemini 和 OpenAI 之间选择 LLM 服务提供商。这满足了项目需求中添加 OpenAI 作为备选方案的要求。该实现遵循了 `spec-pseudocode` 和 `architect` 模式提供的规范。

**Details:**
*   **新模块创建:**
    *   创建了 [`openai_client.py`](openai_client.py:1) 文件，其中包含 `analyze_image_openai(image_path, system_prompt_override=None)` 函数。
    *   此函数处理环境变量加载 (`OPENAI_API_KEY`, `OPENAI_MODEL_NAME`, `OPENAI_BASE_URL`, `DEFAULT_SYSTEM_PROMPT`)，图像的 base64 编码，与 OpenAI API 的交互，以及错误处理和日志记录。
*   **应用逻辑修改 ([`app.py`](app.py:1)):**
    *   在 [`app.py`](app.py:1) 的 `index` 路由中，添加了逻辑以从环境变量 `LLM_PROVIDER` 读取提供商选择。
    *   根据 `LLM_PROVIDER` 的值，动态调用 `openai_client.analyze_image_openai()` 或 `gemini_client.analyze_image()`。
    *   确保将用户自定义的系统提示传递给所选的客户端函数。
    *   添加了对 `openai_client` 模块的导入和错误处理。
*   **配置更新 ([`.env.example`](.env.example:1)):**
    *   向 [`.env.example`](.env.example:1) 添加了新的环境变量：`LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL_NAME`, `OPENAI_BASE_URL` (可选)。
*   **依赖更新 ([`requirements.txt`](requirements.txt:1)):**
    *   将 `openai` Python 库添加到了 [`requirements.txt`](requirements.txt:1)。
*   **系统模式:** 此更改遵循了先前在 [`memory-bank/systemPatterns.md`](memory-bank/systemPatterns.md:1) 中记录的“[LLM 提供商抽象/策略模式]”。
---
### Decision (Code)
[2025-05-13 21:04:29] - 在 Web UI 中实现 LLM 提供商、API 密钥和模型选择功能

**Rationale:**
根据用户反馈，为了增强应用的灵活性和用户控制，在 Web 界面上添加了配置 LLM 提供商、API 密钥和选择模型的功能。用户现在可以直接在 UI 中进行这些设置，并通过浏览器 `localStorage` 保存这些偏好以供后续会话使用。

**Details:**
*   **LLM 客户端修改 (`gemini_client.py`, `openai_client.py`):**
    *   为每个客户端添加了 `list_models(api_key_override=None)` 函数，用于获取相应提供商的可用模型列表。这些函数接受可选的 API 密钥覆盖。
    *   修改了核心分析函数 (`analyze_image` 和 `analyze_image_openai`) 以接受可选的 `api_key_override` 和 `model_name_override` 参数，允许在运行时动态指定 API 密钥和模型。OpenAI 客户端还接受 `base_url_override`。
*   **后端应用修改 ([`app.py`](app.py:1)):**
    *   添加了新的 API 端点 `/api/get_models/<provider>` (POST)，该端点接收提供商名称和可选的 API 密钥（在请求体中），然后调用相应客户端的 `list_models` 函数，并返回模型列表的 JSON 响应。
    *   修改了主 `index` 路由的 `POST` 请求处理逻辑：
        *   从表单数据中接收用户选择的 LLM 提供商 (`llm_provider`)、模型名称 (`selected_model_name`) 以及 Gemini 和 OpenAI 的 API 密钥。
        *   将这些用户提供的值（API 密钥、模型名称）传递给所选 LLM 客户端的分析函数中的相应覆盖参数。
*   **前端模板修改 ([`templates/index.html`](templates/index.html:1)):**
    *   **UI 元素:**
        *   添加了用于选择 LLM 提供商 (Gemini/OpenAI) 的下拉菜单。
        *   为 Gemini 和 OpenAI API 密钥分别添加了密码输入框。
        *   添加了用于显示和选择模型的下拉菜单。
        *   添加了“刷新模型列表”和“保存LLM设置到浏览器”按钮。
    *   **JavaScript 逻辑:**
        *   实现了 `saveLLMSettings()` 函数，用于将用户在表单中输入的 LLM 配置（提供商、API 密钥、模型选择、自定义提示）保存到浏览器的 `localStorage`。
        *   实现了 `loadLLMSettings()` 函数，在页面加载时从 `localStorage` 读取已保存的设置并预填充表单。
        *   实现了 `fetchModels(provider, selectedModelFromStorage)` 函数，通过 AJAX 调用后端的 `/api/get_models/<provider>` 端点来动态获取和填充模型选择下拉菜单。此函数会传递用户在 UI 中输入的 API 密钥。
        *   实现了 `updateApiKeyVisibility()` 函数，根据所选的 LLM 提供商动态显示/隐藏相应的 API 密钥输入框。
        *   添加了事件监听器，以便在提供商选择更改、点击刷新模型按钮或页面加载时触发相应的 JS 函数。
---
### Decision (Code)
[2025-05-13 21:13:01] - 进一步增强 UI：允许 OpenAI Base URL 自定义和手动输入模型名称

**Rationale:**
根据用户进一步的反馈，为了提供更高级的配置选项，特别是在使用自定义 OpenAI 兼容端点或测试特定/未列出模型时，添加了以下功能：
1.  允许用户在 UI 中为 OpenAI 提供商指定一个自定义的 Base URL。
2.  允许用户除了从列表中选择模型外，还可以手动输入一个模型名称，手动输入的名称将优先于列表选择。

**Details:**
*   **后端应用修改 ([`app.py`](app.py:1)):**
    *   修改了 `/api/get_models/openai` 端点，使其能够接受并传递 `base_url` (从请求体获取) 给 `openai_client.list_openai_models` 函数。
    *   更新了主 `index` 路由的 `POST` 请求处理逻辑：
        *   从表单中获取用户输入的 `openai_base_url`。
        *   从表单中获取用户手动输入的 `custom_model_name`。
        *   确定最终使用的模型名称：优先使用 `custom_model_name`，如果为空，则使用从下拉列表选择的 `selected_model_name`。
        *   在调用 `openai_client.analyze_image_openai` 时，传递 `base_url_override` 参数。
*   **前端模板修改 ([`templates/index.html`](templates/index.html:1)):**
    *   **UI 元素:**
        *   在 OpenAI API 密钥输入框下方，为 OpenAI Base URL 添加了一个新的文本输入框 (`id="openai_base_url"`)。此输入框仅在选择 OpenAI 提供商时可见。
        *   在模型选择下拉菜单下方，添加了一个新的文本输入框 (`id="custom_model_name"`)，允许用户手动输入模型名称。
    *   **JavaScript 逻辑:**
        *   更新了 `saveLLMSettings()` 和 `loadLLMSettings()` 函数，以包含对 `openai_base_url` 和 `custom_model_name` 的 `localStorage` 保存和加载。
        *   更新了 `fetchModels()` 函数，在为 OpenAI 获取模型时，会从 UI 读取 `openai_base_url` 并将其包含在发送到后端的 AJAX 请求中。
        *   确保了 OpenAI Base URL 输入框的可见性与 OpenAI API 密钥输入框的可见性同步。
---
### Decision (Code)
[2025-05-13 21:25:51] - 调整 Gemini 模型列表的筛选逻辑

**Rationale:**
根据用户反馈，之前的 Gemini 模型列表筛选过于严格，导致一些用户期望看到的模型（如纯文本模型或某些 vision 模型）未被列出。为了提供更全面的模型选择，同时仍然帮助用户识别主要用于视觉任务的模型，对筛选逻辑进行了调整。

**Details:**
*   **LLM 客户端修改 ([`gemini_client.py`](gemini_client.py:1)):**
    *   修改了 `list_gemini_models` 函数中的筛选逻辑。
    *   现在，该函数会包含所有支持 `generateContent` 方法的 Gemini 模型。
    *   仍然保留了 `is_vision_model` 标志（基于模型名称中的关键字），以便在 UI 中可以对模型进行排序或提供视觉提示，将视觉相关模型优先显示。
    *   最终列表会根据 `is_vision` 标志（视觉模型优先）和显示名称进行排序。
---
### Decision (Architecture)
[YYYY-MM-DD HH:MM:SS] - 选择 Celery 结合 Redis (作为 Broker 和 Backend) 实现多 PDF 文件的异步后台处理。

**Rationale:**
*   **用户体验：** 允许 Flask 应用在提交长时间运行的 PDF 处理任务后立即响应用户，避免请求超时。
*   **可伸缩性：** Celery workers 可以独立扩展以处理更多并发任务。
*   **成熟度与生态：** Celery 是 Python 中广泛使用的分布式任务队列，拥有良好的社区支持和文档。Redis 作为 Broker 和 Backend 配置简单且性能良好。
*   **解耦：** 将耗时的处理逻辑与主 Web 应用分离。

**Implementation Details:**
*   **Celery 应用定义：** 在新模块 `celery_app.py` (或 `tasks.py`) 中定义 Celery app 实例和任务 (如 `process_pdf_celery_task`)。
*   **Flask 集成：** Flask 应用 ([`app.py`](app.py:1)) 将导入 Celery 任务并通过 `.delay()` 或 `.apply_async()` 提交。
*   **配置：** Celery Broker URL 和 Result Backend URL 将通过环境变量配置，并在 `celery_app.py` 中加载。
*   **任务状态反馈：** Flask 应用将提供一个 API 端点 (例如 `/task_status/<task_id>`)，前端通过轮询此端点从 Celery Backend 获取任务状态和结果。

---
### Decision (Architecture)
[YYYY-MM-DD HH:MM:SS] - 在 Celery 任务内部，针对单个 PDF 文件中的多页面分析，采用 `asyncio` 和异步 HTTP 客户端 (如 `aiohttp`) 实现并发 LLM API 调用。

**Rationale:**
*   **效率提升：** 对于单个 PDF 内的多个页面，LLM API 调用是主要的 IO 瓶颈。使用 `asyncio` 可以并发执行这些网络请求，显著减少单个 PDF 的总处理时间。
*   **资源利用：** 在等待 API 响应时，`asyncio` 可以切换到其他任务，提高 CPU 和网络资源的利用率。

**Implementation Details:**
*   **异步工具模块：** 创建新模块 `async_utils.py`，包含核心函数如 `process_pdf_pages_concurrently(image_paths, ...)`。
*   **LLM 客户端：** [`gemini_client.py`](gemini_client.py:1) 和 [`openai_client.py`](openai_client.py:1) 将提供异步接口 (例如 `analyze_image_async`)，这些接口内部使用 `aiohttp` 或相应 SDK 的异步功能。
*   **Celery 任务调用：** `process_pdf_celery_task` (在 `celery_app.py` 中) 在获得 PDF 的所有页面图像后，将调用 `async_utils.process_pdf_pages_concurrently()`。
*   **错误处理：** `async_utils.py` 将负责处理单个页面分析的错误，并汇总结果。

---
### Decision (Architecture)
[YYYY-MM-DD HH:MM:SS] - 实现独立的令牌桶算法模块 (`rate_limiter.py`)，并将其集成到 LLM 客户端中，以控制对外部 LLM API 的调用频率。

**Rationale:**
*   **服务保护：** 防止因调用频率过高而超出外部 LLM API 的服务限制，避免服务中断或额外费用。
*   **系统稳定性：** 确保应用在与外部服务交互时的行为是可预测和可控的。

**Implementation Details:**
*   **模块化实现：** 在 `rate_limiter.py` 中创建 `TokenBucketRateLimiter` 类。
*   **LLM 客户端集成：** [`gemini_client.py`](gemini_client.py:1) 和 [`openai_client.py`](openai_client.py:1) 在其实例化时创建或接收一个速率限制器实例。
*   **调用前检查：** 在 LLM 客户端的（同步和异步）API 调用方法中，实际发出网络请求前，会调用速率限制器的 `consume()` 方法。如果无法获取令牌，则根据策略等待或处理。