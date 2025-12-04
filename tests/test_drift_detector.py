import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drift_detector import analyze_drift

class TestDriftDetector(unittest.TestCase):
    
    @patch('drift_detector.read_context')
    @patch('drift_detector.read_slack_messages')
    def test_analyze_drift_returns_json(self, mock_read_slack, mock_read_context):
        # 1. Mock read_context
        mock_read_context.return_value = "# Project Context\n..."
        
        # 2. Mock read_slack_messages
        mock_read_slack.return_value = [{'text': 'Delayed', 'user': 'U123'}]
        
        # 3. Mock Gemini client
        mock_client = MagicMock()
        mock_response = MagicMock()
        expected_json = {
            "status_change_detected": True,
            "reason": "Test",
            "suggested_update_to_doc": "Update status",
            "risk_level": "High"
        }
        mock_response.text = json.dumps(expected_json)
        mock_client.models.generate_content.return_value = mock_response
        
        # 4. Call analyze_drift
        result = analyze_drift(mock_client, ['C123'])
        
        # 5. Assertions
        self.assertEqual(result, expected_json)
        
        # Verify calls
        mock_read_context.assert_called_once()
        mock_read_slack.assert_called_once_with('C123', limit=20)
        mock_client.models.generate_content.assert_called_once()

    @patch('drift_detector.read_context')
    @patch('drift_detector.read_slack_messages')
    def test_analyze_drift_handles_list_bug(self, mock_read_slack, mock_read_context):
        # 1. Mock read_context
        mock_read_context.return_value = "# Project Context\n..."
        
        # 2. Mock read_slack_messages
        mock_read_slack.return_value = [{'text': 'Delayed', 'user': 'U123'}]
        
        # 3. Mock Gemini client to return a LIST instead of a dict
        mock_client = MagicMock()
        mock_response = MagicMock()
        expected_json = {
            "status_change_detected": True,
            "reason": "Test List Bug",
            "suggested_update_to_doc": "Update status",
            "risk_level": "High"
        }
        # The bug was that Gemini returned [ {...} ]
        mock_response.text = json.dumps([expected_json])
        mock_client.models.generate_content.return_value = mock_response
        
        # 4. Call analyze_drift
        result = analyze_drift(mock_client, ['C123'])
        
        # 5. Assertions
        # Should return the dict inside the list
        self.assertEqual(result, expected_json)

    @patch('drift_detector.read_context')
    @patch('drift_detector.read_slack_messages')
    @patch('drift_detector.get_self_todo')
    def test_drift_detection_with_todo_sync(self, mock_get_todo, mock_read_slack, mock_read_context):
        # 1. Mock dependencies
        mock_read_context.return_value = "Context"
        mock_read_slack.return_value = []
        mock_get_todo.return_value = ["Fix the login bug", "Email Alice"]
        
        # 2. Mock Gemini
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "{}"
        mock_client.models.generate_content.return_value = mock_response
        
        # 3. Call analyze_drift with todo_sync=True
        analyze_drift(mock_client, channel_ids=['C123'], todo_sync=True)
        
        # 4. Verify get_self_todo was called
        mock_get_todo.assert_called_once()
        
        # 5. Verify the prompt contains the To-Do items
        args, kwargs = mock_client.models.generate_content.call_args
        actual_prompt = kwargs.get('contents')
        
        # Check that the To-Do items are present in the prompt string
        self.assertIn("Fix the login bug", actual_prompt)
        self.assertIn("Email Alice", actual_prompt)
        self.assertIn("self-todo", actual_prompt)

if __name__ == '__main__':
    unittest.main()
