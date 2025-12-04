import os
import json
from google.genai import types

def read_context():
    """
    Reads the context.md file.
    Returns the content as a string.
    """
    file_path = "context.md"
    if not os.path.exists(file_path):
        return ""
    
    with open(file_path, "r") as f:
        return f.read()

def parse_context_with_gemini(client, context_text):
    """
    Takes the raw markdown text and the genai.Client object.
    Sends a prompt to the model to extract 'Overall Health' and 'Action Items'.
    Returns the parsed JSON.
    """
    prompt = f"""Extract the 'Overall Health' and the list of 'Action Items' from this markdown. Return ONLY a JSON object.

Markdown Content:
{context_text}
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        # Handle cases where the model might return markdown code blocks
        text = response.text
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

def update_section(section_title, new_content):
    """
    Updates a specific section in context.md.
    
    Args:
        section_title: The title of the section to update (e.g., "1. Critical Status").
                       Matches lines starting with "## " followed by this title.
        new_content: The new content to replace the existing section body with.
        
    Raises:
        ValueError: If the section header is not found.
    """
    import re
    
    file_path = "context.md"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} not found.")
    
    with open(file_path, "r") as f:
        content = f.read()
        
    # Escape the title to handle any special regex characters
    escaped_title = re.escape(section_title)
    
    # Pattern to find the header and its content up to the next header or EOF
    # Group 1: The header line (e.g., "## 1. Critical Status\n")
    # Group 2: The content of the section
    pattern = rf"(##\s+{escaped_title}\s*\n)(.*?)(?=\n##\s+|\Z)"
    
    match = re.search(pattern, content, flags=re.DOTALL)
    
    if not match:
        raise ValueError(f"Section '{section_title}' not found in {file_path}")
    
    # Construct the new content
    # We keep the header (match.group(1)) and replace the body (match.group(2))
    # We ensure the new content ends with a newline for formatting
    clean_new_content = new_content.strip() + "\n"
    
    # Reconstruct the file content
    # content[:match.end(1)] includes the header
    # content[match.end(2):] is the rest of the file starting from the next header (or empty if EOF)
    updated_file_content = content[:match.end(1)] + clean_new_content + content[match.end(2):]
    
    with open(file_path, "w") as f:
        f.write(updated_file_content)
