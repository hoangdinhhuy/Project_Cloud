import time
import logging
import google.generativeai as genai
from config import settings

logger = logging.getLogger(__name__)

class GeminiManager:
    """
    Manages multiple Gemini API keys, handles key rotation on quota/rate limit errors,
    and executes API calls with exponential backoff retry.
    """
    def __init__(self):
        # Load API keys from settings. GEMINI_API_KEY can be a single key or comma-separated list.
        raw_key = settings.GEMINI_API_KEY
        self.api_keys = [k.strip() for k in raw_key.split(",") if k.strip()]
        self.current_key_idx = 0
        
        if not self.api_keys:
            logger.error("❌ No GEMINI_API_KEY configured in settings!")
        else:
            masked_keys = [f"{k[:6]}...{k[-6:]}" if len(k) > 12 else "..." for k in self.api_keys]
            logger.info(f"🔑 GeminiManager initialized with {len(self.api_keys)} key(s): {masked_keys}")
            
        self.configure_current_key()
        
    def configure_current_key(self):
        if not self.api_keys:
            return
        key = self.api_keys[self.current_key_idx]
        masked = f"{key[:8]}...{key[-8:]}" if len(key) > 16 else "..."
        logger.info(f"⚙️ Configuring Gemini API key index {self.current_key_idx} ({masked})")
        genai.configure(api_key=key)
        
    def rotate_key(self) -> bool:
        if len(self.api_keys) <= 1:
            logger.warning("⚠️ Only one Gemini API key is configured. Cannot rotate.")
            return False
        
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        self.configure_current_key()
        return True
        
    def get_model(self, model_name: str = "gemini-flash-latest", tools = None) -> genai.GenerativeModel:
        """Instantiates and returns a new GenerativeModel with the active API key"""
        self.configure_current_key()
        return genai.GenerativeModel(model_name=model_name, tools=tools)
        
    def execute_with_retry(self, operation_func, *args, **kwargs):
        """
        Executes a Gemini operation (like model.generate_content) with retry and key rotation.
        operation_func: A callable that returns the API response.
        """
        max_attempts = max(6, len(self.api_keys) * 2)
        delay = 2.0
        
        for attempt in range(max_attempts):
            try:
                # Always configure current active key before calling
                self.configure_current_key()
                return operation_func()
            except Exception as e:
                err_str = str(e)
                err_type = type(e).__name__
                is_rate_limit = (
                    "429" in err_str or 
                    "quota" in err_str.lower() or 
                    "ResourceExhausted" in err_type or 
                    "ResourceExhausted" in err_str
                )
                
                logger.warning(f"⚠️ Gemini API error (attempt {attempt + 1}/{max_attempts}): [{err_type}] {e}")
                
                if is_rate_limit:
                    logger.info("🔄 Quota exceeded or rate limited. Attempting API key rotation...")
                    if self.rotate_key():
                        logger.info("✅ API Key rotated. Retrying immediately...")
                        continue
                        
                if attempt == max_attempts - 1:
                    logger.error("❌ Gemini API failed after maximum retries.")
                    raise e
                    
                logger.info(f"⏳ Sleeping for {delay:.1f}s before retrying...")
                time.sleep(delay)
                delay = min(delay * 2, 15.0)

# Global shared instance of the manager
gemini_manager = GeminiManager()
