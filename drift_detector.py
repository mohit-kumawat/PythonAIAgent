import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from state_manager import read_context
from slack_tools import read_slack_messages

def analyze_drift(client, channel_id):
    """
    Compares the 'Project Context' (Plan) against the 'Recent Slack Messages' (Reality).
    Looks for discrepancies, completed tasks, or new risks.
    """
    # 1. Read Context
    context_text = read_context()
    
    # 2. Read Slack Messages
    # The user requested limit=20
    slack_messages = read_slack_messages(channel_id, limit=20)
    
    # Convert slack messages to a string representation for the prompt
    # We'll just use the raw list of dicts, converted to string
    slack_messages_str = json.dumps(slack_messages, indent=2, default=str)

    # 3. Prepare Prompt
    system_prompt = "You are a Senior Technical Program Manager. Compare the 'Project Context' (Plan) against the 'Recent Slack Messages' (Reality). Look for discrepancies, completed tasks, or new risks."
    
    user_prompt = f"""Context: {context_text} 

 Slack Messages: {slack_messages_str} 

 Return a JSON object with this schema: {{ 'status_change_detected': boolean, 'reason': string, 'suggested_update_to_doc': string, 'risk_level': 'Low'|'High' }}"""

    # 4. Call Gemini
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json"
        )
    )

    # 5. Return Parsed JSON
    try:
        parsed = json.loads(response.text)
    except json.JSONDecodeError:
        # Fallback for potential markdown wrapping
        text = response.text
        if text.strip().startswith("```json"):
            text = text.strip()[7:]
        if text.strip().endswith("```"):
            text = text.strip()[:-3]
        parsed = json.loads(text.strip())
        
    if isinstance(parsed, list):
        if len(parsed) > 0:
            return parsed[0]
        else:
            return {} # Or raise error
    return parsed

if __name__ == "__main__":
    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found.")
    else:
        client = genai.Client(api_key=api_key)
        # Placeholder channel ID - user to replace
        test_channel_id = "YOUR_CHANNEL_ID" 
        print(f"Running drift analysis for channel: {test_channel_id}...")
        
        # Note: This might return empty messages if the channel ID is invalid, 
        # but it fulfills the requirement to call the function.
        result = analyze_drift(client, test_channel_id)
        print(json.dumps(result, indent=2))
