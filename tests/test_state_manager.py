import unittest
from unittest.mock import patch, mock_open
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state_manager import update_section

class TestStateManager(unittest.TestCase):

    def test_update_section_modifies_target_only(self):
        original_content = """# Project Context

## 1. Critical Status
**Overall Health:** Green

## 2. Release Plan
- [ ] Alpha Release

## 3. Action Items
- [ ] Review PR
"""
        new_status = "**Overall Health:** Red\n**Blockers:** API Down"
        
        # We mock open to read the original content and capture the write
        m = mock_open(read_data=original_content)
        
        # We also need to mock os.path.exists to return True
        with patch('builtins.open', m), patch('os.path.exists', return_value=True):
            update_section("1. Critical Status", new_status)
            
            # Verify the write call
            # We expect the file to be written with the updated content
            handle = m()
            # Get the arguments passed to write
            # There might be multiple calls if chunked, but here it's one write
            # However, mock_open behavior on write can be tricky to inspect the final content if multiple writes.
            # Our function does one f.write(updated_file_content)
            
            args, _ = handle.write.call_args
            written_content = args[0]
            
            # Assertions on the written content
            self.assertIn("**Overall Health:** Red", written_content)
            self.assertIn("**Blockers:** API Down", written_content)
            
            # Ensure other sections are untouched
            self.assertIn("## 2. Release Plan", written_content)
            self.assertIn("- [ ] Alpha Release", written_content)
            
            # Ensure the header itself is still there
            self.assertIn("## 1. Critical Status", written_content)

    def test_update_section_raises_error_if_missing(self):
        original_content = "## 2. Release Plan\n..."
        m = mock_open(read_data=original_content)
        
        with patch('builtins.open', m), patch('os.path.exists', return_value=True):
            with self.assertRaises(ValueError):
                update_section("1. Critical Status", "Content")

if __name__ == '__main__':
    unittest.main()
