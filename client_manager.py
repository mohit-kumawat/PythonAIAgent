import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

class ClientManager:
    def __init__(self):
        # Load keys from environment variables
        # We look for GOOGLE_API_KEY and any GOOGLE_API_KEY_BACKUP* variables
        self.keys = []
        
        # Primary key
        primary = os.environ.get("GOOGLE_API_KEY")
        if primary:
            self.keys.append(primary)
            
        # Backup keys
        backup = os.environ.get("GOOGLE_API_KEY_BACKUP")
        if backup:
            self.keys.append(backup)
            
        # We can also look for numbered backups if we want to be generic, 
        # but for now we stick to the ones explicitly defined.
        
        self.keys = [k for k in self.keys if k] # Filter None
        if not self.keys:
            raise ValueError("No GOOGLE_API_KEY found in environment variables.")
            
        self.current_key_index = 0

    def get_client(self):
        """Returns a genai.Client initialized with the current key."""
        if not self.keys:
            raise ValueError("No API keys available.")
        
        current_key = self.keys[self.current_key_index]
        # print(f"[Debug] Using API Key index: {self.current_key_index}")
        return genai.Client(api_key=current_key)

    def rotate_client(self):
        """Switches to the next available API key and returns a new client."""
        if len(self.keys) <= 1:
            print("Warning: No backup keys available to rotate to.")
            return self.get_client()
            
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        print(f"Rotating API Key. Switching to key index: {self.current_key_index}")
        return self.get_client()
