# PDF 内容分析 Web 应用程序

一个使用 Python Flask 和 Google Gemini API 构建的 Web 应用程序，用于上传 PDF 文件，将其内容转换为图像，通过 Gemini API 分析图像内容，最后在网页上展示结果并支持导出为 Markdown 文件。

## 功能列表

1.  通过 Web 界面上传一个或多个 PDF 文件。
2.  将上传的 PDF 自动转换为每页一张图像。
3.  将图像发送给 Google Gemini API 进行内容分析/OCR。
4.  在 Web 界面上显示分析结果。
5.  支持将每个 PDF 的分析结果导出为 Markdown 文件。
6.  通过 `.env` 文件配置 API 密钥、Gemini 模型和网络代理。

## 技术栈

*   Python 3.x
*   Flask
*   Google Gemini API (via `google-generativeai` library)
*   `pdf2image` (依赖 Poppler)
*   HTML, CSS (用于前端模板)
*   Pillow (PIL Fork)

## 目录结构

```
.
├── app.py                  # Flask 主应用程序
├── pdf_processor.py        # PDF 到图像转换模块
├── gemini_client.py        # Google Gemini API 交互模块
├── requirements.txt        # Python 依赖列表
├── .env.example            # 环境变量配置示例
├── .env                    # (用户创建) 实际环境变量配置文件
├── templates/              # HTML 模板目录
│   ├── index.html          # 文件上传页面
│   └── results.html        # 分析结果展示页面
├── uploads/                # (运行时创建) 存储上传的 PDF 和转换后的图像
├── memory-bank/            # 项目上下文、决策和进度记录
│   ├── productContext.md
│   ├── decisionLog.md
│   └── progress.md
└── README.md               # 本文档
```

## 安装与设置

1.  **获取代码**

    如果您通过 Git 克隆仓库：
    ```bash
    git clone <repository_url>
    cd <project_directory_name>
    ```
    如果直接下载了代码，请解压并进入项目根目录。

2.  **创建并激活虚拟环境 (推荐)**

    ```bash
    python -m venv venv
    ```
    *   Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    *   macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **安装依赖**

    确保虚拟环境已激活，然后运行：
    ```bash
    pip install -r requirements.txt
    ```

4.  **配置环境变量**

    *   复制 `.env.example` 文件到 `.env`：
        ```bash
        # Windows
        copy .env.example .env
        # macOS/Linux
        cp .env.example .env
        ```
        (或者手动复制 [`./.env.example`](./.env.example) 并重命名为 `.env`)
    *   编辑新创建的 `.env` 文件，并填入以下必要的值：
        *   `GEMINI_API_KEY`: **必需。** 您的 Google AI Studio API 密钥。
        *   `FLASK_SECRET_KEY`: **必需。** Flask 应用的密钥，用于保护会话数据。您可以使用以下命令生成一个安全的密钥：
            ```bash
            python -c "import os; print(os.urandom(24).hex())"
            ```
            将生成的字符串粘贴到 `.env` 文件中。
    *   可选配置 (根据您的需求在 `.env` 中设置)：
        *   `HTTP_PROXY` 和 `HTTPS_PROXY`: 如果您的网络环境需要通过代理访问外部服务 (如 Google Gemini API)，请设置这两个变量。例如: `HTTP_PROXY=http://proxy.example.com:8080`
        *   `GEMINI_VISION_MODEL`: 指定用于图像分析的 Gemini 模型。默认为 `gemini-pro-vision`。
        *   `GEMINI_TEXT_MODEL`: 指定用于纯文本处理的 Gemini 模型 (如果应用中有此需求)。默认为 `gemini-pro`。
        *   `POPPLER_PATH`: (主要针对 Windows) 如果 `pdf2image` 无法自动找到 Poppler，您可以在此指定 Poppler 的 `bin` 目录路径。例如: `POPPLER_PATH=C:\path\to\poppler-xx.xx.x\bin`

5.  **安装 `pdf2image` 的外部依赖 (Poppler)**

    `pdf2image` 依赖 Poppler 工具集来处理 PDF 文件。您需要根据您的操作系统安装它：

    *   **Windows:**
        1.  从 [Manish Bhardwaj 的构建](https://github.com/oschwartz10612/poppler-windows/releases/) 或 [conda-forge](https://anaconda.org/conda-forge/poppler) 下载最新的 Poppler 二进制文件。
        2.  解压下载的文件。
        3.  将解压后 Poppler 目录下的 `bin\` 子目录 (例如 `C:\path\to\poppler-0.68.0_x86_64\poppler-0.68.0\bin`) 添加到系统的 `PATH` 环境变量中。
            或者，您可以在 `.env` 文件中设置 `POPPLER_PATH` 变量指向这个 `bin` 目录，如上文“配置环境变量”部分所述。

    *   **macOS (使用 Homebrew):**
        ```bash
        brew install poppler
        ```

    *   **Linux (Debian/Ubuntu):**
        ```bash
        sudo apt-get update && sudo apt-get install -y poppler-utils
        ```

    *   **Linux (Fedora):**
        ```bash
        sudo dnf install -y poppler-utils
        ```

    *   **Conda (跨平台):**
        ```bash
        conda install -c conda-forge poppler
        ```
    有关更多详细信息和故障排除，请参阅 [`pdf2image` 的 PyPI 页面](https://pypi.org/project/pdf2image/) 和 [Poppler 官方网站](https://poppler.freedesktop.org/)。

## 运行应用程序

1.  确保您已完成所有“安装与设置”步骤，并且虚拟环境已激活。
2.  在项目根目录下，运行 Flask 开发服务器：
    ```bash
    python app.py
    ```
3.  应用程序启动后，您应该会在终端看到类似以下的输出：
    ```
     * Serving Flask app 'app'
     * Debug mode: on  (或者 off, 取决于 app.py 中的设置)
     * Running on http://127.0.0.1:5000 (Press CTRL+C to quit)
    ```
4.  打开您的 Web 浏览器并访问：`http://127.0.0.1:5000/`

5.  **自定义运行端口 (可选):**
    默认情况下，应用程序在 5000 端口运行。如果您想更改此端口，可以在启动应用程序之前设置 `FLASK_RUN_PORT` 环境变量。例如，要在端口 8080 上运行：
    *   macOS/Linux:
        ```bash
        export FLASK_RUN_PORT=8080
        python app.py
        ```
    *   Windows (Command Prompt):
        ```bash
        set FLASK_RUN_PORT=8080
        python app.py
        ```
    *   Windows (PowerShell):
        ```bash
        $env:FLASK_RUN_PORT="8080"
        python app.py
        ```
    或者，您可以直接在您的 `.env` 文件中添加 `FLASK_RUN_PORT=your_desired_port`。
## 使用方法

1.  **上传 PDF:**
    *   在应用程序主页 (`http://127.0.0.1:5000/`)，您会看到一个文件上传表单。
    *   点击 "选择文件" (或 "Browse") 按钮，然后选择一个或多个 PDF 文件。
    *   点击 "上传并分析" 按钮提交文件。

2.  **查看结果:**
    *   文件上传和处理完成后，您将被重定向到结果页面。
    *   此页面将显示从每个 PDF 提取的文本内容。

3.  **导出 Markdown:**
    *   在结果页面上，每个成功处理的 PDF 文件旁边会有一个 "导出为 Markdown" 的链接。
    *   点击此链接以下载该 PDF 分析结果的 Markdown 文件。

## (可选) 未来展望

*   支持更多输入文件格式 (如 DOCX, ODT)。
*   集成更高级的图像预处理选项。
*   提供用户账户和历史记录功能。
*   优化大批量文件处理的性能和用户体验。
*   允许用户选择不同的 Gemini 模型进行分析。