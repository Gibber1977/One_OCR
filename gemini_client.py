import os
import google.generativeai as genai
import google.api_core.exceptions # For specific API error handling
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv
import logging
import traceback
import asyncio # For async operations
import httpx # For async client if google-generativeai doesn't provide one directly for all operations

from rate_limiter import TokenBucketRateLimiter

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(module)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

load_dotenv()

# 代理配置检查
HTTP_PROXY = os.getenv("HTTP_PROXY")
HTTPS_PROXY = os.getenv("HTTPS_PROXY")

if HTTP_PROXY:
    logger.info(f"HTTP_PROXY environment variable found: {HTTP_PROXY}")
    # os.environ['HTTP_PROXY'] = HTTP_PROXY #确保它在环境中为子进程设置(如果需要)
if HTTPS_PROXY:
    logger.info(f"HTTPS_PROXY environment variable found: {HTTPS_PROXY}")
    # os.environ['HTTPS_PROXY'] = HTTPS_PROXY #确保它在环境中为子进程设置(如果需要)

if HTTP_PROXY or HTTPS_PROXY:
    logger.warning("Proxy environment variables (HTTP_PROXY/HTTPS_PROXY) are set. "
                   "The google-generativeai library should automatically use them. "
                   "Ensure they are correctly configured if you experience connection issues.")
    logger.warning("Example .env entries for proxy:")
    logger.warning("# HTTP_PROXY=\"http://your_proxy_address:port\"")
    logger.warning("# HTTPS_PROXY=\"http://your_proxy_address:port\" # Note: often the same as HTTP_PROXY for HTTPS traffic via HTTP proxy")
    logger.warning("# Or for authenticated proxies:")
    logger.warning("# HTTPS_PROXY=\"http://user:password@your_proxy_address:port\"")


# 配置 Gemini API
logger.debug("Attempting to load GEMINI_API_KEY from .env...")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
logger.debug(f"Value of GEMINI_API_KEY after os.getenv: '{GEMINI_API_KEY}' (None or empty string means not loaded)")

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY is still not found or is empty after trying to load from .env.")
    # ... (rest of the error messages for API key)
    # raise ValueError("GEMINI_API_KEY not found in environment variables.") # Allow running if key provided via UI
    logger.warning("GEMINI_API_KEY not found in .env. Will rely on UI input if provided.")
# logger.info("GEMINI_API_KEY loaded successfully.") # Moved this log

# Initial configuration if API key is available from .env
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info(f"genai configured initially with API key from .env.")
    except Exception as e:
        logger.error(f"Error during initial genai.configure with .env key: {e}")
else:
    logger.info("GEMINI_API_KEY not in .env. genai not configured at startup. Waiting for UI input or dynamic configuration.")


DEFAULT_SYSTEM_PROMPT = os.getenv("DEFAULT_SYSTEM_PROMPT", "Analyze this image and describe its content.")
logger.info(f"Default system prompt: \"{DEFAULT_SYSTEM_PROMPT}\"")

# 从环境变量加载模型名称，如果未设置则使用默认值
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-1.5-flash-latest")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-1.0-pro") # 或者例如 'gemini-1.5-pro-latest' 如果需要更新的文本模型

logger.info(f"Using Gemini Vision Model: {GEMINI_VISION_MODEL}")
logger.info(f"Using Gemini Text Model (for tests/future use): {GEMINI_TEXT_MODEL}")

# Rate Limiter Configuration
# API_CALLS_PER_SECOND = float(os.getenv("API_CALLS_PER_SECOND", "1")) # e.g., 1 call per second
# API_MAX_TOKENS = float(os.getenv("API_MAX_TOKENS", "5")) # e.g., burst up to 5 calls
# gemini_rate_limiter = TokenBucketRateLimiter(tokens_per_second=API_CALLS_PER_SECOND, max_tokens=API_MAX_TOKENS)
# logger.info(f"Gemini rate limiter configured: {API_CALLS_PER_SECOND} tokens/sec, max {API_MAX_TOKENS} tokens.")

def test_text_generation():
    logger.info("--- Starting Text Generation Test ---")
    request_options = {"timeout": 30}
    try:
        # 使用配置的文本模型
        text_model_name = GEMINI_TEXT_MODEL
        logger.info(f"Using text model: {text_model_name}")
        model = genai.GenerativeModel(text_model_name)
        prompt = "你好，Gemini！请说“测试成功”。"
        logger.info(f"Sending text prompt: \"{prompt}\"")
        logger.info(f"Sending request to Gemini API (model: {text_model_name}) with timeout: {request_options['timeout']}s...")
        response = model.generate_content(prompt, request_options=request_options)
        logger.debug(f"Raw response from text generation: {response}")
        if response and hasattr(response, 'text') and response.text:
            logger.info(f"Text generation successful. Response: \"{response.text.strip()}\"")
            return response.text.strip()
        elif response and response.parts:
             if hasattr(response.parts[0], 'text') and response.parts[0].text is not None:
                logger.info("Successfully extracted text from response.parts[0] for text model.")
                return response.parts[0].text.strip()
        logger.error(f"Text generation failed or produced an empty response. Full response: {response}")
        return "Error: Text generation failed or empty response."
    except google.api_core.exceptions.DeadlineExceeded as dee:
        timeout_val = request_options.get('timeout', 'N/A')
        logger.error(f"Gemini text API call timed out after {timeout_val}s: {dee}")
        return f"Error: Gemini text API call timed out after {timeout_val} seconds. Details: {str(dee)}"
    except google.api_core.exceptions.GoogleAPIError as gae:
        logger.error(f"A Google API error occurred during text generation: {gae}")
        return f"Error: A Google API error occurred during text generation: {str(gae)}"
    except Exception as e:
        logger.error(f"An unexpected error occurred during text generation: {str(e)}\n{traceback.format_exc()}")
        return f"An unexpected error occurred during text generation: {str(e)}"
    finally:
        logger.info("--- Finished Text Generation Test ---")

def analyze_image(image_path, user_prompt=None, system_prompt_override=None, api_key_override=None, model_name_override=None):
    original_env_api_key = GEMINI_API_KEY # Store the key from .env, if any
    temporarily_configured_with_override_key = False
    
    current_api_key_to_use = api_key_override if api_key_override and api_key_override.strip() else original_env_api_key

    if not current_api_key_to_use:
        logger.error("No Gemini API key provided (neither in .env nor via UI). Cannot analyze image.")
        return "Error: Gemini API key not configured."

    try:
        # Configure API key if override is provided and different from .env key, or if .env key was not set
        if api_key_override and api_key_override.strip() and api_key_override != original_env_api_key:
            logger.info(f"Temporarily configuring genai with API key provided via UI.")
            genai.configure(api_key=api_key_override)
            temporarily_configured_with_override_key = True
        elif not original_env_api_key and api_key_override and api_key_override.strip(): # .env key was empty, UI key provided
            logger.info(f"Configuring genai with API key provided via UI (no .env key was set).")
            genai.configure(api_key=api_key_override)
            # No need to "restore" if original_env_api_key was None/empty
        elif not genai.API_KEY: # If somehow not configured yet (e.g. .env key was empty and no override)
             logger.info(f"Configuring genai with current_api_key_to_use as it was not configured.")
             genai.configure(api_key=current_api_key_to_use)


        final_system_prompt = DEFAULT_SYSTEM_PROMPT
        if system_prompt_override and system_prompt_override.strip():
            final_system_prompt = system_prompt_override.strip()
            logger.info(f"Using system_prompt_override for '{image_path}'.")

        request_options = {"timeout": 60}
        logger.info(f"Analyzing image: {image_path} with system prompt: \"{final_system_prompt[:100]}...\"")
        logger.debug(f"Opening image: {image_path}")
        img = Image.open(image_path)
        img.load()
        logger.debug(f"Image loaded: {image_path}, format: {img.format}, mode: {img.mode}, size: {img.size}")
        
        # Model selection
        model_to_use = model_name_override if model_name_override and model_name_override.strip() else GEMINI_VISION_MODEL
        logger.info(f"Using Gemini vision model: {model_to_use}")
        
        model = genai.GenerativeModel(model_to_use, system_instruction=final_system_prompt)
        
        content_parts = []
        if user_prompt and user_prompt.strip():
            content_parts.append(user_prompt.strip())
        content_parts.append(img)

        # Consume a token before making the API call
        # if not gemini_rate_limiter.consume(1):
        #     logger.warning(f"Rate limit exceeded for {image_path}. Waiting for token...")
        #     # Simple busy wait; in a real async scenario, this would be handled differently
        #     # For synchronous, we might just wait or raise an error.
        #     # For this example, let's try to wait once.
        #     import time # Make sure time is imported if not already at top level
        #     time.sleep(1.0 / gemini_rate_limiter.tokens_per_second if gemini_rate_limiter.tokens_per_second > 0 else 1.0)
        #     if not gemini_rate_limiter.consume(1):
        #         logger.error(f"Still rate limited after waiting for {image_path}. Aborting call.")
        #         return f"Error: Rate limit exceeded for {image_path}."
        # logger.info(f"Token consumed for {image_path}. Proceeding with API call.")

        logger.info(f"Sending request to Gemini API (model: {model_to_use}) for image '{image_path}' with timeout: {request_options['timeout']}s...")
        logger.debug(f"Content parts for API: {content_parts}")
        
        response = model.generate_content(content_parts, request_options=request_options)
        logger.debug(f"Raw response from Gemini API for '{image_path}': {response}")
        if response and response.parts:
            if hasattr(response.parts[0], 'text') and response.parts[0].text is not None:
                logger.info(f"Successfully extracted text from response.parts[0] for '{image_path}'.")
                return response.parts[0].text.strip()
            else: 
                if response.prompt_feedback and hasattr(response.prompt_feedback, 'block_reason_message') and response.prompt_feedback.block_reason_message:
                    block_msg = response.prompt_feedback.block_reason_message
                    logger.warning(f"Content generation for '{image_path}' blocked by API (prompt_feedback): {block_msg}")
                    return f"Error: Content generation blocked - {block_msg}"
                if response.candidates:
                    for i, candidate in enumerate(response.candidates):
                        logger.debug(f"Checking candidate {i} for '{image_path}': {candidate}")
                        if hasattr(candidate, 'finish_reason') and candidate.finish_reason != 'STOP' and candidate.finish_reason != 'FINISH_REASON_UNSPECIFIED':
                            reason = candidate.finish_reason
                            safety_ratings_str = f" Safety ratings: {candidate.safety_ratings}" if hasattr(candidate, 'safety_ratings') else ""
                            error_msg = f"Content generation for '{image_path}' stopped. Finish reason: {reason}.{safety_ratings_str}"
                            logger.warning(error_msg)
                            return f"Error: {error_msg}"
                logger.error(f"No text in response.parts[0] for '{image_path}' and no clear blocking reason. Parts: {response.parts}")
                return f"Error: No text found in Gemini API response part for '{image_path}'."
        elif response and hasattr(response, 'text') and response.text is not None: 
            logger.info(f"Successfully extracted text from response.text (fallback) for '{image_path}'.")
            return response.text.strip()
        logger.error(f"Unexpected response structure or empty response from Gemini API for '{image_path}'. Full response: {response}")
        return f"Error: Unexpected or empty response from Gemini API for '{image_path}'."
    except FileNotFoundError:
        logger.error(f"Image file not found: {image_path}")
        return f"Error: Image file not found at {image_path}"
    except UnidentifiedImageError:
        logger.error(f"Cannot identify image file (possibly corrupt or unsupported format): {image_path}")
        return f"Error: Cannot identify image file (corrupt or unsupported format): {image_path}"
    except genai.types.generation_types.BlockedPromptException as bpe:
        logger.error(f"Gemini API request for '{image_path}' blocked due to prompt content: {bpe}")
        return f"Error: Gemini API request for '{image_path}' was blocked. Reason: {bpe}"
    except google.api_core.exceptions.DeadlineExceeded as dee:
        timeout_val = request_options.get('timeout', 'N/A')
        logger.error(f"Gemini API call for '{image_path}' timed out after {timeout_val}s: {dee}")
        return f"Error: Gemini API call for '{image_path}' timed out after {timeout_val} seconds. Details: {str(dee)}"
    except google.api_core.exceptions.GoogleAPIError as gae: # Catching more general Google API errors
        logger.error(f"A Google API error occurred for '{image_path}': {gae}. This could be due to proxy issues, authentication, or quotas.")
        return f"Error: A Google API error occurred for '{image_path}': {str(gae)}"
    except Exception as e:
        logger.error(f"An unexpected error occurred in analyze_image for '{image_path}': {str(e)}\n{traceback.format_exc()}")
        return f"An unexpected error occurred while analyzing the image '{image_path}': {str(e)}"
    finally:
        if temporarily_configured_with_override_key and original_env_api_key:
            logger.info(f"Restoring genai configuration with original API key from .env.")
            try:
                genai.configure(api_key=original_env_api_key)
            except Exception as e_restore:
                logger.error(f"Error restoring genai configuration with .env key: {e_restore}")
        elif temporarily_configured_with_override_key and not original_env_api_key:
            # If we used an override key because the .env key was missing,
            # there's no "original" state to restore to that involves a key.
            # We could try to "unconfigure" but genai library might not support that directly.
            # For now, we'll leave it configured with the override key if no .env key existed.
            logger.info("Original .env API key was not set; genai remains configured with the UI-provided key for this session.")


def analyze_images_batch(image_paths, user_prompt=None, system_prompt_override=None, api_key_override=None, model_name_override=None):
        results = []
        logger.info(f"Starting batch analysis for {len(image_paths)} images.")
        for image_path in image_paths:
            analysis = analyze_image(
                image_path,
                user_prompt=user_prompt,
                system_prompt_override=system_prompt_override,
                api_key_override=api_key_override,
                model_name_override=model_name_override
            )
            results.append({'image_path': image_path, 'analysis': analysis})
        logger.info(f"Finished batch analysis for {len(image_paths)} images.")
        return results
    
def list_gemini_models(api_key_override=None):
        """Lists available Gemini models, prioritizing vision models."""
        original_env_api_key = GEMINI_API_KEY
        temporarily_configured = False
        current_api_key_to_use = api_key_override if api_key_override and api_key_override.strip() else original_env_api_key
    
        if not current_api_key_to_use:
            logger.error("No Gemini API key available to list models.")
            return {"error": "API key not configured."}
    
        try:
            if api_key_override and api_key_override.strip() and api_key_override != original_env_api_key:
                logger.info("Temporarily configuring genai with provided API key to list models.")
                genai.configure(api_key=api_key_override)
                temporarily_configured = True
            elif not original_env_api_key and api_key_override and api_key_override.strip():
                logger.info("Configuring genai with provided API key to list models (no .env key).")
                genai.configure(api_key=api_key_override)
            # If no override and no .env key, current_api_key_to_use would be None,
            # and we would have already returned an error.
            # If .env key was used for initial config, and no override, we use that.
            # If an override was provided and is different, it's handled above.
            # This explicit check for genai.API_KEY is problematic and not needed
            # as current_api_key_to_use should be the source of truth for the key in this function.
            # We ensure genai is configured if a key is available.
            # The initial configuration at module load handles the .env key.
            # The temporary configuration handles the override.
            # If current_api_key_to_use is set, we assume genai will be/is configured with it.
            # No need for: elif not genai.API_KEY:
    
    
            logger.info("Fetching list of Gemini models...")
            models_info = []
            for m in genai.list_models():
                # We are interested in models that support 'generateContent' for vision tasks
                if 'generateContent' in m.supported_generation_methods:
                    # Prioritize models clearly marked for vision or multimodal
                    is_vision_model = any(keyword in m.name.lower() or keyword in m.display_name.lower()
                                          for keyword in ['vision', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-ultra', 'multimodal'])
                    
                    # Include some known good text models as well, if needed for other purposes, but prioritize vision
                    # Now, we include all models that support 'generateContent'.
                    # The 'is_vision_model' flag can still be useful for client-side sorting or display hints.
                    models_info.append({
                        "id": m.name,
                        "display_name": m.display_name,
                        "description": m.description,
                        "version": m.version,
                        "is_vision": is_vision_model # Keep the flag for potential UI hints
                    })
            
            # Sort to bring likely vision models (based on keywords) to the top, then by display name
            models_info.sort(key=lambda x: (not x['is_vision'], x['display_name'].lower()))
            
            logger.info(f"Found {len(models_info)} relevant Gemini models.")
            return {"models": models_info}
        except Exception as e:
            logger.error(f"Error listing Gemini models: {e}\n{traceback.format_exc()}")
            return {"error": f"Failed to list Gemini models: {str(e)}"}
        finally:
            if temporarily_configured and original_env_api_key:
                logger.info("Restoring genai configuration with original .env API key after listing models.")
                try:
                    genai.configure(api_key=original_env_api_key)
                except Exception as e_restore:
                    logger.error(f"Error restoring genai configuration: {e_restore}")
            elif temporarily_configured and not original_env_api_key:
                logger.info("Original .env API key was not set; genai remains configured with the UI-provided key for this session.")

async def analyze_image_async(image_path, user_prompt=None, system_prompt_override=None, api_key_override=None, model_name_override=None):
    """
    Asynchronously analyzes an image using the Gemini API.
    Includes rate limiting and API key handling.
    """
    original_env_api_key = GEMINI_API_KEY
    temporarily_configured_with_override_key = False
    
    current_api_key_to_use = api_key_override if api_key_override and api_key_override.strip() else original_env_api_key

    if not current_api_key_to_use:
        logger.error("Async: No Gemini API key provided. Cannot analyze image.")
        return "Error: Gemini API key not configured."

    try:
        if api_key_override and api_key_override.strip() and api_key_override != original_env_api_key:
            logger.info(f"Async: Temporarily configuring genai with API key provided via UI.")
            # genai.configure is synchronous, ensure this is okay in async context or find async alternative if exists
            genai.configure(api_key=api_key_override)
            temporarily_configured_with_override_key = True
        elif not original_env_api_key and api_key_override and api_key_override.strip():
            logger.info(f"Async: Configuring genai with API key provided via UI (no .env key was set).")
            genai.configure(api_key=api_key_override)
        elif not genai.API_KEY: # Check if genai is configured at all
             logger.info(f"Async: Configuring genai with current_api_key_to_use as it was not configured.")
             genai.configure(api_key=current_api_key_to_use)

        final_system_prompt = DEFAULT_SYSTEM_PROMPT
        if system_prompt_override and system_prompt_override.strip():
            final_system_prompt = system_prompt_override.strip()
            logger.info(f"Async: Using system_prompt_override for '{image_path}'.")

        request_options = {"timeout": 60} # Timeout for the async call
        logger.info(f"Async: Analyzing image: {image_path} with system prompt: \"{final_system_prompt[:100]}...\"")
        
        # Asynchronously open image if it becomes a bottleneck, for now, keep it sync
        # In a high-throughput Celery worker, disk I/O might also benefit from async via libraries like aiofiles
        img = Image.open(image_path)
        img.load() # Ensure image data is loaded
        logger.debug(f"Async: Image loaded: {image_path}, format: {img.format}, mode: {img.mode}, size: {img.size}")
        
        model_to_use = model_name_override if model_name_override and model_name_override.strip() else GEMINI_VISION_MODEL
        logger.info(f"Async: Using Gemini vision model: {model_to_use}")
        
        # google-generativeai uses an internal http client that should handle async correctly
        model = genai.GenerativeModel(model_to_use, system_instruction=final_system_prompt)
        
        content_parts = []
        if user_prompt and user_prompt.strip():
            content_parts.append(user_prompt.strip())
        content_parts.append(img) # PIL Image object

        # Asynchronously consume a token from the rate limiter
        # await gemini_rate_limiter.consume_async(1)
        # logger.info(f"Async: Token consumed for {image_path}. Proceeding with API call.")

        logger.info(f"Async: Sending request to Gemini API (model: {model_to_use}) for image '{image_path}' with timeout: {request_options['timeout']}s...")
        
        response = await model.generate_content_async(content_parts, request_options=request_options)
        logger.debug(f"Async: Raw response from Gemini API for '{image_path}': {response}")

        if response and response.parts:
            if hasattr(response.parts[0], 'text') and response.parts[0].text is not None:
                logger.info(f"Async: Successfully extracted text from response.parts[0] for '{image_path}'.")
                return response.parts[0].text.strip()
            else:
                # Handle blocked prompts or other issues similar to synchronous version
                if response.prompt_feedback and hasattr(response.prompt_feedback, 'block_reason_message') and response.prompt_feedback.block_reason_message:
                    block_msg = response.prompt_feedback.block_reason_message
                    logger.warning(f"Async: Content generation for '{image_path}' blocked by API: {block_msg}")
                    return f"Error: Content generation blocked - {block_msg}"
                if response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'finish_reason') and candidate.finish_reason != 'STOP' and candidate.finish_reason != 'FINISH_REASON_UNSPECIFIED': # Added FINISH_REASON_UNSPECIFIED
                            reason = candidate.finish_reason
                            safety_str = f" Safety: {candidate.safety_ratings}" if hasattr(candidate, 'safety_ratings') else ""
                            error_msg = f"Async: Content generation for '{image_path}' stopped. Reason: {reason}.{safety_str}"
                            logger.warning(error_msg)
                            return f"Error: {error_msg}"
                logger.error(f"Async: No text in response.parts[0] for '{image_path}' and no clear blocking reason. Parts: {response.parts}")
                return f"Error: No text found in Gemini API response part for '{image_path}'."
        elif response and hasattr(response, 'text') and response.text is not None:
            logger.info(f"Async: Successfully extracted text from response.text (fallback) for '{image_path}'.")
            return response.text.strip()
        logger.error(f"Async: Unexpected response structure or empty response from Gemini API for '{image_path}'.")
        return f"Error: Unexpected or empty response from Gemini API for '{image_path}'."

    except FileNotFoundError:
        logger.error(f"Async: Image file not found: {image_path}")
        return f"Error: Image file not found at {image_path}"
    except UnidentifiedImageError:
        logger.error(f"Async: Cannot identify image file: {image_path}")
        return f"Error: Cannot identify image file: {image_path}"
    except genai.types.generation_types.BlockedPromptException as bpe:
        logger.error(f"Async: Gemini API request for '{image_path}' blocked: {bpe}")
        return f"Error: Gemini API request for '{image_path}' was blocked. Reason: {bpe}"
    except google.api_core.exceptions.DeadlineExceeded as dee:
        timeout_val = request_options.get('timeout', 'N/A')
        logger.error(f"Async: Gemini API call for '{image_path}' timed out after {timeout_val}s: {dee}")
        return f"Error: Gemini API call for '{image_path}' timed out. Details: {str(dee)}"
    except google.api_core.exceptions.GoogleAPIError as gae:
        logger.error(f"Async: A Google API error occurred for '{image_path}': {gae}")
        return f"Error: A Google API error occurred for '{image_path}': {str(gae)}"
    except Exception as e:
        logger.error(f"Async: An unexpected error occurred for '{image_path}': {str(e)}\n{traceback.format_exc()}")
        return f"An unexpected error occurred: {str(e)}"
    finally:
        if temporarily_configured_with_override_key and original_env_api_key:
            logger.info(f"Async: Restoring genai configuration with original API key from .env.")
            genai.configure(api_key=original_env_api_key) # Synchronous configure
        elif temporarily_configured_with_override_key and not original_env_api_key:
            logger.info("Async: Original .env API key was not set; genai remains configured with the UI-provided key.")


async def main_async_test():
    logger.info("\n--- Starting Async Image Analysis Test ---")
    dummy_image_path_async = "dummy_test_image_async.png"
    try:
        if not os.path.exists(dummy_image_path_async):
            from PIL import Image as PImage, ImageDraw
            img_create = PImage.new('RGB', (220, 60), color = (200, 200, 240))
            d = ImageDraw.Draw(img_create)
            d.text((10,10), "Async Test Image - Hello Gemini", fill=(0,0,50))
            img_create.save(dummy_image_path_async)
            logger.info(f"Created dummy async image: {dummy_image_path_async}")

        # Test async analysis
        logger.info("Testing analyze_image_async...")
        async_result = await analyze_image_async(dummy_image_path_async, user_prompt="Describe this async test image.")
        logger.info(f"Async image analysis result: {async_result}")

        # Test multiple async calls concurrently
        logger.info("\n--- Testing multiple async calls concurrently ---")
        tasks = [
            analyze_image_async(dummy_image_path_async, user_prompt=f"Concurrent call {i+1}") for i in range(3)
        ]
        results = await asyncio.gather(*tasks)
        for i, res in enumerate(results):
            logger.info(f"Concurrent async result {i+1}: {res}")

    except ImportError:
        logger.error("Pillow library (PIL) is not installed. Skipping async dummy image creation.")
    except Exception as e:
        logger.error(f"An error occurred during the async image analysis test: {e}\n{traceback.format_exc()}")
    logger.info("--- Async Image Analysis Test Finished ---")


if __name__ == '__main__':
    logger.info("Starting gemini_client.py test script...")
    logger.info(f"GEMINI_API_KEY loaded: {'Yes' if GEMINI_API_KEY else 'No'}")
    # DEFAULT_SYSTEM_PROMPT is already logged when defined

    # DEFAULT_SYSTEM_PROMPT is already logged when defined

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set. Skipping API tests.")
    else:
        # text_result = test_text_generation() # Temporarily commented out due to model availability issues.
        # logger.info(f"Text Generation Test Result: {text_result}") # See note in test_text_generation function.
        # logger.info("If pure text generation testing is needed, uncomment the above and ensure a valid text model is used.")
        # logger.info("You can use client.list_models() to find available models.")
        
        logger.info("\n--- Proceeding to Image Analysis Test ---")
        dummy_image_path = "dummy_test_image.png"
        try:
            if not os.path.exists(dummy_image_path):
                logger.info(f"Dummy image '{dummy_image_path}' not found, creating it...")
                from PIL import Image as PImage, ImageDraw
                img_create = PImage.new('RGB', (200, 50), color = (220, 220, 220))
                d = ImageDraw.Draw(img_create)
                d.text((10,10), "Test Image - Hello World", fill=(0,0,0))
                img_create.save(dummy_image_path)
                logger.info(f"Created dummy image: {dummy_image_path}")
            else:
                logger.info(f"Dummy image '{dummy_image_path}' already exists.")
            
            # Test with default system prompt
            logger.info("Testing analyze_image with default system prompt (using .env key if available)...")
            single_result_default_prompt = analyze_image(dummy_image_path, user_prompt="Describe this dummy image.")
            logger.info(f"Single image analysis result (default prompt, .env key): {single_result_default_prompt}")

            # Test with a custom system prompt override (using .env key if available)
            logger.info("Testing analyze_image with a custom system prompt override (using .env key if available)...")
            custom_prompt_for_test = "You are a very brief assistant. Describe the image in 5 words."
            single_result_custom_prompt = analyze_image(dummy_image_path, user_prompt="What is this?", system_prompt_override=custom_prompt_for_test)
            logger.info(f"Single image analysis result (custom prompt, .env key): {single_result_custom_prompt}")

            # Test listing models (using .env key if available)
            logger.info("\n--- Testing Model Listing (using .env key if available) ---")
            models_data = list_gemini_models()
            if "models" in models_data:
                logger.info(f"Available Gemini Models (first 5): {models_data['models'][:5]}")
            else:
                logger.error(f"Failed to list models: {models_data.get('error')}")

            # Example of testing with an overridden API key (replace with a valid test key if you have one)
            # test_override_api_key = "YOUR_TEST_GEMINI_API_KEY_HERE_IF_DIFFERENT"
            # if test_override_api_key != "YOUR_TEST_GEMINI_API_KEY_HERE_IF_DIFFERENT" and test_override_api_key:
            #     logger.info(f"\n--- Testing with Overridden API Key: {test_override_api_key[:10]}... ---")
            #     models_with_override = list_gemini_models(api_key_override=test_override_api_key)
            #     if "models" in models_with_override:
            #         logger.info(f"Available Gemini Models with override key (first 5): {models_with_override['models'][:5]}")
            #     else:
            #         logger.error(f"Failed to list models with override key: {models_with_override.get('error')}")
            #
            #     logger.info("Testing analyze_image with overridden API key...")
            #     result_with_override_key = analyze_image(dummy_image_path, user_prompt="Describe with override key.", api_key_override=test_override_api_key)
            #     logger.info(f"Analysis with override key: {result_with_override_key}")
            # else:
            #     logger.info("\nSkipping tests with overridden API key as no test key was provided in the script.")

        except ImportError:
            logger.error("Pillow library (PIL) is not installed. Skipping dummy image creation and tests that require it.")
        except Exception as e:
            logger.error(f"An error occurred during the image analysis test script execution: {e}\n{traceback.format_exc()}")
    
    # Run async tests if API key is available
    if GEMINI_API_KEY:
        asyncio.run(main_async_test())
            
    logger.info("--- gemini_client.py test script finished ---")