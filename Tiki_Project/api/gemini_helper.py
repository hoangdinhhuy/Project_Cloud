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
        
        # Available models list for fallback (ordered by priority/cost/speed)
        self.models = ["gemini-flash-latest", "gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro"]
        self.current_model_idx = 0
        
        if not self.api_keys:
            logger.error("❌ No GEMINI_API_KEY configured in settings!")
        else:
            masked_keys = [f"{k[:6]}...{k[-6:]}" if len(k) > 12 else "..." for k in self.api_keys]
            logger.info(f"🔑 GeminiManager initialized with {len(self.api_keys)} key(s): {masked_keys}")
            logger.info(f"🤖 Configured fallback models: {self.models}")
            
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

    def rotate_model(self) -> bool:
        if len(self.models) <= 1:
            logger.warning("⚠️ Only one Gemini model is configured. Cannot rotate model.")
            return False
        self.current_model_idx = (self.current_model_idx + 1) % len(self.models)
        logger.info(f"🔄 Switched active model to: {self.get_current_model_name()}")
        return True

    def get_current_model_name(self) -> str:
        return self.models[self.current_model_idx]

    def rotate_key_or_model(self) -> bool:
        """
        Rotates the API key. If a full cycle of keys has been exhausted,
        it rotates the model to the next one and resets key index to 0.
        Returns True if a rotation took place, False otherwise.
        """
        if not self.api_keys:
            return self.rotate_model()
            
        if len(self.api_keys) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            self.configure_current_key()
            
            # If we wrapped around to index 0, it means all keys were tried. Let's rotate the model!
            if self.current_key_idx == 0:
                logger.info("🔄 All Gemini API keys exhausted for current model. Rotating model...")
                self.rotate_model()
            return True
        else:
            # If we only have 1 API key, try rotating the model
            logger.info("🔄 Single Gemini API key configured. Rotating model...")
            return self.rotate_model()
        
    def get_model(self, model_name: str = "gemini-flash-latest", tools = None) -> genai.GenerativeModel:
        """Instantiates and returns a new GenerativeModel with the active API key and model"""
        self.configure_current_key()
        
        # Resolve 'gemini-flash-latest' to the active model in rotation
        if model_name == "gemini-flash-latest":
            model_name = self.get_current_model_name()
            
        logger.info(f"🤖 Instantiating model: {model_name}")
        return genai.GenerativeModel(model_name=model_name, tools=tools)
        
    def execute_with_retry(self, operation_func, *args, **kwargs):
        """
        Executes a Gemini operation (like model.generate_content) with retry and key/model rotation.
        operation_func: A callable that returns the API response.
        """
        max_attempts = max(8, len(self.api_keys) * len(self.models) * 2)
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
                    logger.info("🔄 Quota exceeded or rate limited. Attempting API key or model rotation...")
                    if self.rotate_key_or_model():
                        logger.info("✅ Rotation successful. Retrying immediately...")
                        continue
                        
                if attempt == max_attempts - 1:
                    logger.error("❌ Gemini API failed after maximum retries.")
                    raise e
                    
                logger.info(f"⏳ Sleeping for {delay:.1f}s before retrying...")
                time.sleep(delay)
                delay = min(delay * 2, 15.0)

# Global shared instance of the manager
gemini_manager = GeminiManager()
