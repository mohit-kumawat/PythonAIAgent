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
        result = analyze_drift(mock_client, 'C123')
        
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
        result = analyze_drift(mock_client, 'C123')
        
        # 5. Assertions
        # Should return the dict inside the list
        self.assertEqual(result, expected_json)

if __name__ == '__main__':
    unittest.main()
