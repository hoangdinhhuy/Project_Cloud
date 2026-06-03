import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure the api directory is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings

class TestGeminiManagerRobustness(unittest.TestCase):
    def setUp(self):
        settings.GEMINI_API_KEY = "test_key_1,test_key_2"
        
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_key_rotation_on_429(self, mock_generative_model, mock_configure):
        from gemini_helper import GeminiManager
        
        manager = GeminiManager()
        self.assertEqual(len(manager.api_keys), 2)
        self.assertEqual(manager.current_key_idx, 0)
        
        call_count = 0
        def mock_operation():
            nonlocal call_count
            call_count += 1
            if manager.current_key_idx == 0:
                raise Exception("ResourceExhausted: 429 Quota exceeded")
            else:
                return "SuccessResponse"
                
        response = manager.execute_with_retry(mock_operation)
        
        self.assertEqual(response, "SuccessResponse")
        self.assertEqual(call_count, 2)
        self.assertEqual(manager.current_key_idx, 1)
        print("✅ Key rotation test passed successfully!")

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_chat_assistant_rotation(self, mock_generative_model, mock_configure):
        from gemini_helper import GeminiManager
        from chat_assistant import AIBusinessAssistant
        
        manager = GeminiManager()
        manager.api_keys = ["key_A", "key_B"]
        manager.current_key_idx = 0
        
        mock_model_instance = MagicMock()
        mock_generative_model.return_value = mock_model_instance
        
        # Configure both the class mock and the instance mock to return the instance
        mock_generative_model.return_value = mock_model_instance
        
        mock_chat = MagicMock()
        mock_chat.history = ["Msg 1", "Msg 2"]
        
        # Make model return mock_chat when start_chat is called
        mock_model_instance.start_chat.return_value = mock_chat
        
        mock_search_engine = MagicMock()
        assistant = AIBusinessAssistant(search_engine=mock_search_engine)
        assistant.model = mock_model_instance
        
        with patch('chat_assistant.gemini_manager', manager):
            send_count = 0
            def mock_send(msg):
                nonlocal send_count
                send_count += 1
                if manager.current_key_idx == 0:
                    raise Exception("429 ResourceExhausted: Quota reached")
                mock_response = MagicMock()
                mock_response.text = "Hello back!"
                return mock_response
                
            mock_chat.send_message.side_effect = mock_send
            
            response, active_chat = assistant._send_chat_message_with_retry(mock_chat, "Hello")
            
            self.assertEqual(response.text, "Hello back!")
            self.assertEqual(manager.current_key_idx, 1)
            self.assertEqual(send_count, 2)
            print("✅ Chat assistant key rotation and session re-hydration test passed!")

if __name__ == "__main__":
    unittest.main()
