import base64
import os
import logging
import asyncio # For async operations
import httpx # For async client
from openai import OpenAI, AsyncOpenAI # Import AsyncOpenAI
from dotenv import load_dotenv

# from rate_limiter import TokenBucketRateLimiter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API Key and Model from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4-vision-preview")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") # Optional, for custom endpoints
DEFAULT_SYSTEM_PROMPT = os.getenv("DEFAULT_SYSTEM_PROMPT", "Analyze this image and describe its content.")

# Rate Limiter Configuration - assuming same env vars for now, can be made specific
# API_CALLS_PER_SECOND_OPENAI = float(os.getenv("API_CALLS_PER_SECOND_OPENAI", os.getenv("API_CALLS_PER_SECOND", "1")))
# API_MAX_TOKENS_OPENAI = float(os.getenv("API_MAX_TOKENS_OPENAI", os.getenv("API_MAX_TOKENS", "5")))
# openai_rate_limiter = TokenBucketRateLimiter(tokens_per_second=API_CALLS_PER_SECOND_OPENAI, max_tokens=API_MAX_TOKENS_OPENAI)
# logging.info(f"OpenAI rate limiter configured: {API_CALLS_PER_SECOND_OPENAI} tokens/sec, max {API_MAX_TOKENS_OPENAI} tokens.")


if not OPENAI_API_KEY:
    logging.warning("OPENAI_API_KEY not found in .env. Will rely on UI input if provided.")

# Initialize OpenAI client - this will be the default client if no overrides are given
# It might fail if OPENAI_API_KEY is not set, which is handled in analyze_image_openai
_default_client = None
_default_async_client = None # For async operations

if OPENAI_API_KEY:
    try:
        if OPENAI_BASE_URL:
            _default_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
            _default_async_client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        else:
            _default_client = OpenAI(api_key=OPENAI_API_KEY)
            _default_async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        logging.info("Default OpenAI sync and async clients initialized with .env settings.")
    except Exception as e:
        logging.error(f"Failed to initialize default OpenAI clients with .env settings: {e}")
        _default_client = None
        _default_async_client = None
else:
    logging.info("Default OpenAI clients not initialized as OPENAI_API_KEY is missing in .env.")


def encode_image_to_base64(image_path):
    """Encodes a local image file to a base64 string."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        logging.error(f"Image file not found: {image_path}")
        return None
    except Exception as e:
        logging.error(f"Error encoding image {image_path}: {e}")
        return None

def analyze_image_openai(
    image_path: str,
    system_prompt_override: str = None,
    api_key_override: str = None,
    model_name_override: str = None,
    base_url_override: str = None
) -> str | None:
    """
    Analyzes an image using the OpenAI API, allowing for API key and model overrides.

    Args:
        image_path: Path to the local image file.
        system_prompt_override: Optional system prompt to override the default.
        api_key_override: Optional API key to use instead of the one from .env.
        model_name_override: Optional model name to use.
        base_url_override: Optional base URL for the OpenAI API.

    Returns:
        The analysis text from OpenAI, or None if an error occurs.
    """
    current_api_key = api_key_override if api_key_override and api_key_override.strip() else OPENAI_API_KEY
    current_base_url = base_url_override if base_url_override and base_url_override.strip() else OPENAI_BASE_URL
    current_model_name = model_name_override if model_name_override and model_name_override.strip() else OPENAI_MODEL_NAME

    if not current_api_key:
        logging.error("OpenAI API key is not configured (neither in .env nor via UI). Cannot analyze image.")
        return "Error: OpenAI API key not configured."

    # Determine which client to use
    active_client = _default_client
    # If overrides are present that differ from the default client's config, create a temporary client
    if (api_key_override and api_key_override != OPENAI_API_KEY) or \
       (base_url_override and base_url_override != OPENAI_BASE_URL) or \
       (not _default_client and current_api_key): # If default client failed to init but we have a key now
        try:
            logging.info("Creating temporary OpenAI client due to override or missing default client.")
            if current_base_url:
                active_client = OpenAI(api_key=current_api_key, base_url=current_base_url)
            else:
                active_client = OpenAI(api_key=current_api_key)
        except Exception as e:
            logging.error(f"Failed to initialize temporary OpenAI client with overrides: {e}")
            return f"Error: Failed to initialize OpenAI client: {e}"
    
    if not active_client:
        logging.error("OpenAI client could not be initialized. Cannot analyze image.")
        return "Error: OpenAI client initialization failed."


    base64_image = encode_image_to_base64(image_path)
    if not base64_image:
        return "Error: Could not encode image."

    final_system_prompt = system_prompt_override if system_prompt_override and system_prompt_override.strip() else DEFAULT_SYSTEM_PROMPT
    
    logging.info(f"Analyzing image {image_path} with OpenAI model {current_model_name} using system prompt: '{final_system_prompt}'")

    # Consume a token before making the API call
    # if not openai_rate_limiter.consume(1):
    #     logging.warning(f"OpenAI rate limit exceeded for {image_path}. Waiting for token...")
    #     import time # Ensure time is imported
    #     time.sleep(1.0 / openai_rate_limiter.tokens_per_second if openai_rate_limiter.tokens_per_second > 0 else 1.0)
    #     if not openai_rate_limiter.consume(1):
    #         logging.error(f"Still rate limited after waiting for OpenAI call for {image_path}. Aborting.")
    #         return f"Error: OpenAI Rate limit exceeded for {image_path}."
    # logging.info(f"OpenAI token consumed for {image_path}. Proceeding with API call.")

    try:
        response = active_client.chat.completions.create(
            model=current_model_name,
            messages=[
                {
                    "role": "system",
                    "content": final_system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}" # Assuming PNG, adjust if other formats are common
                            }
                        }
                    ]
                }
            ],
            max_tokens=1024 # Adjust as needed
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            analysis_text = response.choices[0].message.content.strip()
            logging.info(f"OpenAI analysis successful for {image_path}.")
            return analysis_text
        else:
            logging.error(f"OpenAI API response did not contain expected content for {image_path}. Response: {response}")
            return "Error: OpenAI API response was empty or malformed."

    except Exception as e:
        logging.error(f"Error during OpenAI API call for {image_path}: {e}")
        if "OPENAI_API_KEY" in str(e).upper() or "AUTHENTICATION" in str(e).upper():
             return "Error: OpenAI API request failed. Check API key and permissions."
        return f"Error: An exception occurred during OpenAI API call: {e}"

def list_openai_models(api_key_override: str = None, base_url_override: str = None):
    """
    Lists available OpenAI models, attempting to filter for vision-capable ones.
    """
    current_api_key = api_key_override if api_key_override and api_key_override.strip() else OPENAI_API_KEY
    current_base_url = base_url_override if base_url_override and base_url_override.strip() else OPENAI_BASE_URL

    if not current_api_key:
        logging.error("OpenAI API key not configured to list models.")
        return {"error": "API key not configured."}

    temp_client = None
    try:
        if current_base_url:
            temp_client = OpenAI(api_key=current_api_key, base_url=current_base_url)
        else:
            temp_client = OpenAI(api_key=current_api_key)
        logging.info("Fetching list of OpenAI models...")
        
        models_list = temp_client.models.list()
        
        processed_models = []
        if models_list and models_list.data:
            for model in models_list.data:
                # OpenAI API doesn't explicitly flag vision models in the same way as Gemini.
                # We rely on known model ID patterns or if they are general purpose and might support vision.
                model_id = model.id.lower()
                is_likely_vision = "vision" in model_id or "gpt-4-turbo" in model_id or "gpt-4o" in model_id
                
                processed_models.append({
                    "id": model.id,
                    "display_name": model.id, # OpenAI API often just returns ID
                    "owned_by": model.owned_by,
                    "is_vision_capable": is_likely_vision # Best guess
                })
            # Sort, perhaps prioritizing known vision models
            processed_models.sort(key=lambda x: (not x['is_vision_capable'], x['id']))
            logging.info(f"Found {len(processed_models)} OpenAI models.")
            return {"models": processed_models}
        else:
            logging.warning("No models returned from OpenAI API or data was empty.")
            return {"models": []}
            
    except Exception as e:
        logging.error(f"Error listing OpenAI models: {e}")
        return {"error": f"Failed to list OpenAI models: {str(e)}"}

async def analyze_image_openai_async(
    image_path: str,
    system_prompt_override: str = None,
    api_key_override: str = None,
    model_name_override: str = None,
    base_url_override: str = None
) -> str | None:
    """
    Asynchronously analyzes an image using the OpenAI API.
    """
    current_api_key = api_key_override if api_key_override and api_key_override.strip() else OPENAI_API_KEY
    current_base_url = base_url_override if base_url_override and base_url_override.strip() else OPENAI_BASE_URL
    current_model_name = model_name_override if model_name_override and model_name_override.strip() else OPENAI_MODEL_NAME

    if not current_api_key:
        logging.error("Async OpenAI: API key is not configured. Cannot analyze image.")
        return "Error: OpenAI API key not configured."

    active_async_client = _default_async_client
    if (api_key_override and api_key_override != OPENAI_API_KEY) or \
       (base_url_override and base_url_override != OPENAI_BASE_URL) or \
       (not _default_async_client and current_api_key):
        try:
            logging.info("Async OpenAI: Creating temporary async client due to override or missing default.")
            if current_base_url:
                active_async_client = AsyncOpenAI(api_key=current_api_key, base_url=current_base_url)
            else:
                active_async_client = AsyncOpenAI(api_key=current_api_key)
        except Exception as e:
            logging.error(f"Async OpenAI: Failed to initialize temporary async client: {e}")
            return f"Error: Failed to initialize OpenAI async client: {e}"
    
    if not active_async_client:
        logging.error("Async OpenAI: Client could not be initialized.")
        return "Error: OpenAI async client initialization failed."

    base64_image = encode_image_to_base64(image_path) # This is sync, consider aiofiles for full async
    if not base64_image:
        return "Error: Could not encode image."

    final_system_prompt = system_prompt_override if system_prompt_override and system_prompt_override.strip() else DEFAULT_SYSTEM_PROMPT
    
    logging.info(f"Async OpenAI: Analyzing {image_path} with model {current_model_name}")

    # await openai_rate_limiter.consume_async(1)
    # logging.info(f"Async OpenAI: Token consumed for {image_path}. Proceeding.")

    try:
        response = await active_async_client.chat.completions.create(
            model=current_model_name,
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]}
            ],
            max_tokens=1024
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            analysis_text = response.choices[0].message.content.strip()
            logging.info(f"Async OpenAI: Analysis successful for {image_path}.")
            return analysis_text
        else:
            logging.error(f"Async OpenAI: API response did not contain expected content for {image_path}.")
            return "Error: OpenAI API response was empty or malformed."

    except Exception as e:
        logging.error(f"Async OpenAI: Error during API call for {image_path}: {e}")
        return f"Error: An exception occurred during async OpenAI API call: {e}"


async def main_async_openai_test():
    logging.info("\n--- Starting Async OpenAI Image Analysis Test ---")
    dummy_image_path_async_openai = "dummy_test_image_async_openai.png"
    if not os.path.exists(dummy_image_path_async_openai):
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (120, 40), color = (0, 255, 0))
            d = ImageDraw.Draw(img)
            d.text((10,10), "Async OpenAI", fill=(0,0,0))
            img.save(dummy_image_path_async_openai)
            logging.info(f"Created dummy async openai image: {dummy_image_path_async_openai}")
        except Exception as e:
            logging.error(f"Could not create dummy image for async openai test: {e}")
            return

    if os.path.exists(dummy_image_path_async_openai) and OPENAI_API_KEY:
        logging.info(f"Testing async OpenAI client with image: {dummy_image_path_async_openai}")
        async_result = await analyze_image_openai_async(dummy_image_path_async_openai)
        logging.info(f"Async OpenAI Analysis Result: {async_result}")

        logging.info("\n--- Testing multiple async OpenAI calls concurrently ---")
        tasks = [
            analyze_image_openai_async(dummy_image_path_async_openai, system_prompt_override=f"Concurrent async OpenAI call {i+1}") for i in range(3)
        ]
        results = await asyncio.gather(*tasks)
        for i, res in enumerate(results):
            logging.info(f"Concurrent async OpenAI result {i+1}: {res}")
    elif not OPENAI_API_KEY:
        logging.warning("Skipping async OpenAI image analysis test: OPENAI_API_KEY not set.")
    else:
        logging.warning(f"Skipping async OpenAI image analysis test: Dummy image '{dummy_image_path_async_openai}' not found.")
    logging.info("--- Async OpenAI Image Analysis Test Finished ---")


if __name__ == '__main__':
    # This is a simple test.
    # Ensure you have a .env file with OPENAI_API_KEY and a test image.
    # Create a dummy image file for testing if it doesn't exist
    dummy_image_path = "dummy_test_image.png"
    if not os.path.exists(dummy_image_path):
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (100, 30), color = (255, 0, 0))
            d = ImageDraw.Draw(img)
            d.text((10,10), "Hello", fill=(0,0,0))
            img.save(dummy_image_path)
            logging.info(f"Created dummy test image: {dummy_image_path}")
        except ImportError:
            logging.warning("Pillow library is not installed. Cannot create a dummy image for testing openai_client.py. Please create 'dummy_test_image.png' manually.")
        except Exception as e:
            logging.error(f"Could not create dummy image: {e}")

    # Test model listing first (requires API key in .env or passed directly)
    if OPENAI_API_KEY:
        logging.info("\n--- Testing OpenAI Model Listing (using .env key) ---")
        models_data = list_openai_models()
        if "models" in models_data:
            logging.info(f"Available OpenAI Models (first 5): {models_data['models'][:5]}")
        else:
            logging.error(f"Failed to list OpenAI models: {models_data.get('error')}")
    else:
        logging.warning("Skipping OpenAI model listing test: OPENAI_API_KEY not set in .env.")


    if os.path.exists(dummy_image_path) and OPENAI_API_KEY:
        logging.info(f"\n--- Testing OpenAI Image Analysis (using .env key) ---")
        logging.info(f"Testing OpenAI client with image: {dummy_image_path}")
        # Test with default system prompt
        analysis_result_default = analyze_image_openai(dummy_image_path)
        if analysis_result_default:
            logging.info(f"Default Prompt Analysis Result:\n{analysis_result_default}\n")
        else:
            logging.error("Failed to get analysis with default prompt.")

        # Test with a custom system prompt
        custom_prompt = "What color is in this image?"
        analysis_result_custom = analyze_image_openai(dummy_image_path, system_prompt_override=custom_prompt)
        if analysis_result_custom:
            logging.info(f"Custom Prompt ('{custom_prompt}') Analysis Result:\n{analysis_result_custom}\n")
        else:
            logging.error("Failed to get analysis with custom prompt.")
        
        # Example: Test with model_name_override (if you have another model like gpt-4-turbo)
        # analysis_result_turbo = analyze_image_openai(dummy_image_path, model_name_override="gpt-4-turbo")
        # if analysis_result_turbo:
        #     logging.info(f"GPT-4-Turbo Analysis Result:\n{analysis_result_turbo}\n")
        # else:
        #     logging.error("Failed to get analysis with gpt-4-turbo.")

    elif not OPENAI_API_KEY:
        logging.warning("Skipping OpenAI image analysis test: OPENAI_API_KEY not set.")
    else:
        logging.warning(f"Skipping OpenAI image analysis test: Dummy image '{dummy_image_path}' not found and could not be created.")

    # Run async tests
    if OPENAI_API_KEY: # Also run async tests if key is available
        asyncio.run(main_async_openai_test())