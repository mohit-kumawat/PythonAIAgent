import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drift_detector import analyze_drift

class TestDriftPrompt(unittest.TestCase):
    
    @patch('drift_detector.read_context')
    @patch('drift_detector.read_slack_messages')
    def test_analyze_drift_prompt_contains_instruction(self, mock_read_slack, mock_read_context):
        # 1. Mock dependencies
        mock_read_context.return_value = "Context"
        mock_read_slack.return_value = []
        
        # 2. Mock Gemini client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "{}" # Dummy valid JSON
        mock_client.models.generate_content.return_value = mock_response
        
        # 3. Call analyze_drift
        analyze_drift(mock_client, 'C123')
        
        # 4. Verify the prompt sent to the model
        # Get the arguments passed to generate_content
        args, kwargs = mock_client.models.generate_content.call_args
        
        # The prompt is passed as 'contents' argument (either positional or keyword)
        # Based on the code: client.models.generate_content(model=..., contents=user_prompt, ...)
        # It's likely passed as a keyword argument 'contents' or positional.
        
        if 'contents' in kwargs:
            actual_prompt = kwargs['contents']
        else:
            # Assuming 'model' is first, 'contents' is second if positional? 
            # The code uses named args mostly but let's check args[0] if kwargs is empty?
            # Actually the code is: client.models.generate_content(model="...", contents=user_prompt, ...)
            # So it should be in kwargs['contents']
            actual_prompt = kwargs.get('contents')
            
        self.assertIsNotNone(actual_prompt, "Prompt content was not found in call args")
        
        # 5. Assert the specific string is present
        expected_instruction = "The EXACT full markdown content for the section to replace the current content"
        self.assertIn(expected_instruction, actual_prompt)

if __name__ == '__main__':
    unittest.main()
