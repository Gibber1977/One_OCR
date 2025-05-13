# System Patterns *Optional*

This file documents recurring patterns and standards used in the project.
It is optional, but recommended to be updated as the project evolves.
2025-05-13 19:11:45 - Log of updates made.

*

## Coding Patterns

*   **Modular Design:** 功能被划分为独立的 Python 模块 (`pdf_processor.py`, `gemini_client.py`, `app.py`) 以提高代码组织性和可维护性。
*   **Configuration Management:** 使用 `.env` 文件和 `python-dotenv` 库管理敏感配置（如 API 密钥），避免硬编码。
*   **Error Handling:** （待定）在适当的位置实现稳健的错误处理机制，例如处理文件上传错误、PDF转换失败或 API 调用异常。
*   **Logging:** （待定）集成日志记录以帮助调试和监控应用程序行为。

## Architectural Patterns

*   **Client-Server Architecture:** Web 浏览器作为客户端，Flask 应用程序作为服务器端。
*   **Model-View-Controller (MVC) like (Flask context):**
    *   **Model:** 数据处理逻辑（例如，`pdf_processor.py` 中的 PDF 内容，`gemini_client.py` 处理的数据）。
    *   **View:** Flask 模板 (`.html` 文件) 负责用户界面的表示。
    *   **Controller:** Flask 路由函数 (`app.py` 中的 `@app.route(...)`) 处理用户请求并将模型和视图连接起来。
*   **API Integration:** 通过 `gemini_client.py` 模块与外部 Google Gemini API 进行交互。

---
### [LLM 提供商抽象/策略模式]
[2025-05-13 20:33:00] - 为了支持多个 LLM 提供商 (例如 Gemini, OpenAI)，将在应用程序中引入一个抽象层。`app.py` 将根据配置动态选择和实例化相应的 LLM 客户端。这允许在不修改核心应用逻辑的情况下轻松切换或添加新的 LLM 提供商。每个 LLM 客户端模块 (例如 `gemini_client.py`, `openai_client.py`) 将实现一个共同的接口，供 `app.py` 调用。
---
### [任务队列 (Celery 与 Redis/RabbitMQ)]
[YYYY-MM-DD HH:MM:SS] - 为了处理耗时的多 PDF 分析任务而不阻塞用户界面，引入了 Celery 分布式任务队列。
*   **应用场景:** 用户上传多个 PDF 文件后，Flask 应用将为每个 PDF 创建一个 Celery 任务，并立即返回响应。
*   **组件:**
    *   **Flask 应用 ([`app.py`](app.py:1)):** 作为任务生产者，将任务发送到消息代理。
    *   **Celery Tasks (`celery_app.py`):** 定义具体的后台处理逻辑，例如 `process_pdf_celery_task`。
    *   **Message Broker (消息代理):** 使用 Redis (推荐，也可作为 Backend) 或 RabbitMQ 传递任务消息。
    *   **Result Backend (结果后端):** 使用 Redis 存储任务的执行状态和结果。
    *   **Celery Workers:** 独立的进程，消费来自消息代理的任务并执行。
*   **交互流程:** Flask 应用提交任务 -> Broker -> Worker 执行任务 (包括调用 `pdf_processor`, `async_utils`, LLM 客户端) -> Worker 将结果存入 Backend -> Flask 应用通过任务 ID 从 Backend 查询状态/结果并反馈给用户。
*   **优点:** 提高应用响应性、可伸缩性、解耦耗时操作。

---
### [IO密集型操作的并发处理 (`asyncio`)]
[YYYY-MM-DD HH:MM:SS] - 对于单个 PDF 文件内多页面的 LLM API 调用（IO密集型操作），在 Celery 任务的执行上下文中采用 `asyncio` 实现并发。
*   **应用场景:** Celery 任务 (`process_pdf_celery_task`) 在处理单个 PDF 时，会将其所有页面图像的分析请求并发地发送给 LLM API。
*   **实现 (`async_utils.py`):**
    *   使用 `asyncio.gather` 同时运行多个页面的 LLM API 调用协程。
    *   LLM 客户端 ([`gemini_client.py`](gemini_client.py:1), [`openai_client.py`](openai_client.py:1)) 提供异步接口 (例如，使用 `aiohttp` 或 SDK 内置的异步支持)。
*   **优点:** 大幅减少单个 PDF 文件内多页面处理的总等待时间，提高资源利用率。

---
### [API 速率限制 (令牌桶算法)]
[YYYY-MM-DD HH:MM:SS] - 为了防止对外部 LLM API 的调用超出其频率限制，实现了一个基于令牌桶算法的速率限制器。
*   **应用场景:** 在 LLM 客户端 ([`gemini_client.py`](gemini_client.py:1), [`openai_client.py`](openai_client.py:1)) 每次向外部 LLM API 发送请求之前，都会先从速率限制器获取令牌。
*   **实现 (`rate_limiter.py`):**
    *   `TokenBucketRateLimiter` 类维护一个令牌桶，按预设速率（如每秒 N 个请求）添加令牌，桶有最大容量。
    *   请求 API 前需消耗令牌；若无足够令牌，则请求可能需要等待或被拒绝（根据实现策略）。
*   **优点:** 保护系统免受 API 服务商的速率限制策略影响，提高系统稳定性和可靠性。
## Testing Patterns

*   （待定）单元测试：针对各个模块（`pdf_processor.py`, `gemini_client.py`）编写单元测试。
*   （待定）集成测试：测试模块之间的交互以及与 Flask 应用程序的集成。
*   （待定）端到端测试：模拟用户操作，测试整个应用程序流程。