# Active Context

This file tracks the project's current status, including recent changes, current goals, and open questions.
2025-05-13 19:11:17 - Log of updates made.

*

## Current Focus

* [2025-05-13 21:58:19] - **Current Focus:** 继续实施异步处理和响应优化功能。已创建 `async_utils.py` 模块。
* [2025-05-13 21:57:22] - **Current Focus:** 继续实施异步处理和响应优化功能。已创建 `celery_app.py` 模块。
* [2025-05-13 21:56:19] - **Current Focus:** 开始实施异步处理和响应优化功能。已创建 `rate_limiter.py` 模块。
* [YYYY-MM-DD HH:MM:SS] - **Current Focus:** 完成了 "One_OCR" 项目异步处理和响应优化功能的详细系统架构设计 ([`architecture_design.md`](architecture_design.md:1))。下一步是根据此架构实现相关组件。
* [2025-05-13 20:35:00] - 当前焦点是规划和设计新的应用程序增强功能：可自定义系统提示和支持 OpenAI 作为备选 LLM。
*   [2025-05-13 19:13:46] - 应用程序架构设计已完成。等待后续步骤（例如，审查或开始实施）。

*   [2025-05-13 19:16:44] - 完成了 PDF 内容分析 Web 应用程序核心功能的代码实现，包括 `app.py`, `pdf_processor.py`, `gemini_client.py`, `templates/index.html`, `templates/results.html`, `requirements.txt`, 和 `.env.example`。
## Recent Changes
* [2025-05-13 20:36:00] - 完成了“可自定义系统提示”功能的代码实现。修改了 [`templates/index.html`](templates/index.html:1) 以添加 UI 输入，更新了 [`app.py`](app.py:1) 以处理后端逻辑和提示传递，并修改了 [`gemini_client.py`](gemini_client.py:1) 的 `analyze_image` ([`gemini_client.py:104`](gemini_client.py:104)) 函数以接受和使用系统提示覆盖。

*   [2025-05-13 19:13:46] - 创建了详细的应用程序架构设计文档 (`architecture_design.md`)。
*   [2025-05-13 19:11:58] - 内存银行初始化完成 (`productContext.md`, `activeContext.md`, `progress.md`, `decisionLog.md`, `systemPatterns.md` 已创建并填充初始内容)。
*   创建了 `memory-bank/productContext.md` 并记录了项目目标、关键特性和初步架构概念。

## Open Questions/Issues

*   暂无。
*   [2025-05-13 19:34:20] - 调试 Gemini API 在 `gemini_client.py` 中的挂起问题。通过添加更详细的日志记录、API 调用超时、更改为更稳定的模型 (`gemini-1.5-flash-latest`) 以及增强错误处理和响应解析来修改 `gemini_client.py`。
*   [2025-05-13 19:40:17] - 进一步调试 `gemini_client.py` 中的 API 调用挂起问题。添加了 `test_text_generation()` 函数以隔离问题是否特定于图像分析。测试脚本现在将首先运行此纯文本测试。
*   [2025-05-13 19:42:29] - 根据用户反馈（使用了网络代理），修改 `gemini_client.py` 以在启动时检查并记录 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量。指导用户在 `.env` 文件中配置这些变量。
*   [2025-05-13 19:45:30] - 在 `gemini_client.py` 的 `test_text_generation` 函数中，将文本模型从 `gemini-pro` 修正为 `gemini-1.0-pro`，以解决之前日志中出现的 "model not found" 错误。核心的 API 调用挂起问题已通过代理配置解决。
*   [2025-05-13 19:47:19] - 在 `gemini_client.py` 中暂时注释掉了对 `test_text_generation()` 函数的调用，因为它使用的文本模型 (`gemini-1.0-pro`) 仍然报告为不可用。核心的图像分析功能已确认正常工作。
*   [2025-05-13 19:50:13] - **Current Focus:** 完成了 Gemini API 模型选择灵活性的实现。用户现在可以通过 `.env` 文件配置 `GEMINI_VISION_MODEL` 和 `GEMINI_TEXT_MODEL`。
*   [2025-05-13 19:50:13] - **Recent Changes:**
    *   修改了 [`gemini_client.py`](gemini_client.py:1) 以从环境变量加载视觉和文本模型名称，并更新了 `analyze_image` ([`gemini_client.py:97`](gemini_client.py:97)) 和 `test_text_generation()` ([`gemini_client.py:62`](gemini_client.py:62)) 函数以使用这些配置。
    *   更新了 [`.env.example`](.env.example:1) 以包含 `GEMINI_VISION_MODEL` 和 `GEMINI_TEXT_MODEL` 的示例。
*   [2025-05-13 19:53:31] - **Current Focus:** 实现了 PDF 处理模块 ([`pdf_processor.py`](pdf_processor.py:1)) 的核心功能。
*   [2025-05-13 19:56:20] - **Current Focus:** 完成 Flask Web 应用程序 ([`app.py`](app.py:1)) 和前端模板 ([`templates/index.html`](templates/index.html:1), [`templates/results.html`](templates/results.html:1)) 的实现。
*   [2025-05-13 20:02:16] - **Current Focus:** 完成了对 Flask 应用的批量上传和 Markdown 导出功能的实现。
*   [2025-05-13 19:53:31] - **Recent Changes:**
    *   更新了 [`pdf_processor.py`](pdf_processor.py:1) 以支持将 PDF 页面转换为图像，并将它们保存到基于 PDF 文件名的特定子目录中 (例如 `uploads/pdf_images/filename_images/page_1.png`)。
    *   添加了对输出图像 DPI 和格式 (PNG, JPEG 等) 的可配置支持。
    *   增强了错误处理和日志记录。
    *   更新了模块内的测试脚本以反映这些更改。
*   [2025-05-13 19:56:31] - **Recent Changes:**
    *   实现了 Flask 应用 ([`app.py`](app.py:1))，包括文件上传、PDF 处理调用、Gemini API 调用和结果显示路由。
    *   创建了用于文件上传的 HTML 模板 ([`templates/index.html`](templates/index.html:1))。
    *   创建了用于显示分析结果的 HTML 模板 ([`templates/results.html`](templates/results.html:1))。
    *   添加了用于提供上传图像的路由 (`/uploads_img/<path:filepath>`)。
    *   确认 [`requirements.txt`](requirements.txt:1) 已包含 Flask 和 python-dotenv。
*   [2025-05-13 20:02:24] - **Recent Changes (批量上传和 Markdown 导出):**
    *   **批量上传:**
        *   更新了 [`templates/index.html`](templates/index.html:1) 以允许选择多个文件 (input `multiple` 属性) 并相应更新了文件名显示逻辑。
        *   修改了 [`app.py`](app.py:1) 中的 `index` 路由以使用 `request.files.getlist("file")` 处理多个文件。
        *   调整了 [`app.py`](app.py:1) 中的结果处理逻辑，以迭代处理每个上传的文件，并为 [`templates/results.html`](templates/results.html:1) 准备包含所有文件结果的聚合数据结构。
        *   更新了 [`templates/results.html`](templates/results.html:1) 以正确显示来自多个 PDF 文件的结果，每个文件一个单独的区域。
    *   **Markdown 导出:**
        *   在 [`app.py`](app.py:1) 中添加了 `app.config['PROCESSED_DATA_CACHE']` 以在内存中缓存成功处理的文件的分析结果。
        *   在 [`app.py`](app.py:1) 中实现了新的路由 `/export_markdown/<original_filename>`，该路由:
            *   从缓存中检索指定文件的分析数据。
            *   将数据格式化为 Markdown 字符串。
            *   通过 Flask `Response` 对象提供 Markdown 内容作为文件下载。
        *   在 [`templates/results.html`](templates/results.html:1) 中为每个成功处理的文件结果旁边添加了“导出为 Markdown”按钮。
* [2025-05-13 20:10:17] - [Debug Status Update: Fixed `NameError: name 'Response' is not defined` in `app.py` by importing `Response` from `flask`.]
* [2025-05-13 20:13:03] - **Current Focus:** 完成了批量导出 Markdown 为 ZIP 文件的功能。
* [2025-05-13 20:13:03] - **Recent Changes:**
    *   在 [`app.py`](app.py:1) 中添加了 `/export_all_markdown_zip` 路由 ([`app.py:215`](app.py:215))，用于生成包含所有已处理文件 Markdown 的 ZIP 压缩包。
    *   更新了 [`app.py`](app.py:1) 的导入，加入了 `io`, `zipfile` 和 `send_file`。
    *   在 [`templates/results.html`](templates/results.html:1) 中添加了“全部导出为 Markdown (ZIP)”按钮 ([`templates/results.html:53`](templates/results.html:53))，链接到新路由。
* [2025-05-13 20:15:10] - **Current Focus:** 完成了 Flask 应用端口可配置性的实现。
* [2025-05-13 20:15:10] - **Recent Changes:**
    *   修改了 [`app.py`](app.py:1) ([`app.py:313`](app.py:313)) 以支持通过 `FLASK_RUN_PORT` 环境变量配置运行端口，默认为 5000。
    *   更新了 [`.env.example`](.env.example:1) 以添加 `FLASK_RUN_PORT` 示例。
    *   更新了 [`README.md`](README.md:1) 以记录如何配置运行端口。
* [2025-05-13 20:39:28] - **Current Focus:** 完成了“支持 OpenAI 作为备选 LLM 服务提供商”功能的代码实现。
* [2025-05-13 20:39:28] - **Recent Changes:**
    *   创建了新文件 [`openai_client.py`](openai_client.py:1) 并实现了其核心逻辑，包括 `analyze_image_openai` 函数。
    *   修改了 [`app.py`](app.py:1) 以包含基于 `LLM_PROVIDER` 环境变量的提供商选择逻辑，并相应调用 `gemini_client` 或 `openai_client`。
    *   更新了 [`.env.example`](.env.example:1) 以包含新的 OpenAI 相关环境变量 (`LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL_NAME`, `OPENAI_BASE_URL`)。
    *   更新了 [`requirements.txt`](requirements.txt:1) 以包含 `openai` 库。
* [2025-05-13 21:04:54] - **Current Focus:** 完成了在 Web UI 中实现 LLM 提供商、API 密钥和模型选择功能。
* [2025-05-13 21:04:54] - **Recent Changes:**
    *   **LLM 客户端 (`gemini_client.py`, `openai_client.py`):**
        *   添加了 `list_models(api_key_override=None)` 函数以列出可用模型。
        *   修改了分析函数以接受 `api_key_override` 和 `model_name_override`。
    *   **后端应用 (`app.py`):**
        *   添加了 `/api/get_models/<provider>` (POST) 端点，用于根据提供商和 API 密钥获取模型列表。
        *   更新了 `index` 路由的 `POST` 逻辑，以从表单接收 LLM 配置（提供商、API 密钥、模型名称）并将其传递给相应的 LLM 客户端。
    *   **前端模板 (`templates/index.html`):**
        *   添加了用于选择 LLM 提供商、输入 API 密钥和选择模型的 UI 元素。
        *   实现了 JavaScript 逻辑，用于：
            *   从 `localStorage` 加载和保存 LLM 设置。
            *   动态显示/隐藏 API 密钥输入框。
            *   通过 AJAX 从后端获取并填充模型列表。
* [2025-05-13 21:13:23] - **Current Focus:** 完成了对 UI 的进一步增强，允许用户为 OpenAI 配置自定义 Base URL，并为任一提供商手动输入模型名称。
* [2025-05-13 21:13:23] - **Recent Changes:**
    *   **后端应用 (`app.py`):**
        *   更新了 `/api/get_models/openai` 端点，以接受并使用请求中提供的 `base_url`。
        *   更新了 `index` 路由的 `POST` 逻辑，以处理来自 UI 的 `openai_base_url` 和 `custom_model_name` 输入，并在调用 LLM 客户端时优先使用手动输入的模型名称。
    *   **前端模板 (`templates/index.html`):**
        *   为 OpenAI Base URL 添加了新的文本输入框。
        *   为手动输入模型名称添加了新的文本输入框。
        *   更新了 JavaScript 逻辑 (`saveLLMSettings`, `loadLLMSettings`, `fetchModels`) 以处理这些新增的输入字段及其在 `localStorage` 中的保存与加载。
* [2025-05-13 21:26:10] - **Current Focus:** 调整了 Gemini 模型列表的筛选逻辑。
* [2025-05-13 21:26:10] - **Recent Changes:**
    *   **LLM 客户端 (`gemini_client.py`):** 修改了 `list_gemini_models` 函数，以包含所有支持 `generateContent` 方法的 Gemini 模型，而不仅仅是名称中包含特定视觉关键字的模型。保留了 `is_vision` 标志用于前端可能的排序或提示。