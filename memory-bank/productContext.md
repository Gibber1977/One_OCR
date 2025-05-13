# Product Context

This file provides a high-level overview of the project and the expected product that will be created. Initially it is based upon projectBrief.md (if provided) and all other available project-related information in the working directory. This file is intended to be updated as the project evolves, and should be used to inform all other modes of the project's goals and context.
2025-05-13 19:11:00 - Log of updates made will be appended as footnotes to the end of this file.

*

## Project Goal

*   开发一个使用 Python 和 Flask 的 Web 应用程序，允许用户上传 PDF，将其转换为图像，使用 Google Gemini API 分析图像内容（OCR 或内容分析），并在 Web 界面上显示结果。

## Key Features

*   PDF 上传功能
*   PDF 到图像的转换（每页一个图像）
*   与 Google Gemini API 集成以进行内容分析/OCR
*   使用 Flask 构建的 Web 用户界面
*   通过环境变量安全管理 API 密钥
*   使用用户提供的默认系统提示与 Gemini API 交互
*   在 Web 界面上清晰显示从 Gemini API 收到的文本结果
*   **新:** 用户可自定义的系统提示，用于指导 LLM 分析。
*   **新:** 支持 OpenAI API 作为备选 LLM 提供商。
*   **新:** **异步处理单个PDF内的页面：** 使用 `asyncio` 和异步HTTP客户端并发处理页面，提高单文件处理效率。
*   **新:** **后台任务队列处理多个PDF文件：** 使用 Celery 和 Redis/RabbitMQ 实现后台任务队列，允许即时用户响应并处理耗时任务。
*   **新:** **API调用频率控制：** 实现基于令牌桶算法的速率限制器，应用于对外部 LLM API 的调用。
*   **新:** **异步任务状态反馈：** 用户可以查看后台任务的处理状态和最终结果。

## Overall Architecture

*   **Frontend (Web Interface):** 使用 Flask 模板 ([`templates/index.html`](templates/index.html:1) 用于文件上传, [`templates/results.html`](templates/results.html:1) 用于显示任务状态和结果)。
*   **Backend (Application Logic):** Flask 应用程序 ([`app.py`](app.py:1)) 负责路由、接收用户请求、将任务提交到 Celery 队列、提供任务状态查询接口。
*   **PDF Processing Module ([`pdf_processor.py`](pdf_processor.py:1)):** 负责将上传的 PDF 文件转换为一系列图像。
*   **LLM Client Modules ([`gemini_client.py`](gemini_client.py:1), [`openai_client.py`](openai_client.py:1)):** 负责与外部 LLM API 通信，发送图像并检索分析结果，内部集成速率限制。将提供异步接口。
*   **Asynchronous Task Queue (Celery):**
*   **Celery App/Tasks (`celery_app.py`):** 定义 Celery 应用和后台任务。
*   **Message Broker (Redis/RabbitMQ):** 用于 Celery 任务的消息传递。
*   **Result Backend (Redis):** 存储 Celery 任务的状态和结果。
*   **Celery Workers:** 执行后台任务的独立进程。
*   **Asynchronous Utilities (`async_utils.py`):** 包含使用 `asyncio` 并发处理 PDF 页面的逻辑，被 Celery 任务调用。
*   **Rate Limiter (`rate_limiter.py`):** 实现令牌桶算法，供 LLM 客户端使用。
*   **Configuration:** API 密钥、Celery Broker/Backend URL 等将通过 `.env` 文件进行管理，项目依赖项将在 [`requirements.txt`](requirements.txt:1) 中列出。
[2025-05-13 20:32:00] - 添加了可自定义系统提示和 OpenAI 支持作为新的关键特性。