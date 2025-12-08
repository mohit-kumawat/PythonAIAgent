#!/usr/bin/env python3
"""
Pre-deployment verification script.
Checks if all required configurations are in place before deploying to Render.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def check_env_var(name, required=True):
    """Check if an environment variable is set"""
    value = os.environ.get(name)
    if value:
        # Mask sensitive values
        if 'TOKEN' in name or 'KEY' in name or 'PASSWORD' in name:
            display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
        else:
            display_value = value
        print(f"✅ {name}: {display_value}")
        return True
    else:
        if required:
            print(f"❌ {name}: NOT SET (REQUIRED)")
        else:
            print(f"⚠️  {name}: NOT SET (OPTIONAL)")
        return not required

def main():
    print("=" * 60)
    print("🔍 Render Deployment Pre-Check")
    print("=" * 60)
    print()
    
    all_good = True
    
    print("📱 Slack Configuration:")
    all_good &= check_env_var("SLACK_BOT_TOKEN")
    all_good &= check_env_var("SLACK_USER_TOKEN")
    all_good &= check_env_var("SLACK_BOT_USER_ID")
    all_good &= check_env_var("SLACK_USER_ID")
    all_good &= check_env_var("SLACK_CHANNELS")
    print()
    
    print("🤖 Google AI Configuration:")
    all_good &= check_env_var("GOOGLE_API_KEY")
    print()
    
    print("📧 Email Configuration (Optional):")
    check_env_var("USER_EMAIL", required=False)
    check_env_var("SMTP_HOST", required=False)
    check_env_var("SMTP_PORT", required=False)
    check_env_var("SMTP_USER", required=False)
    check_env_var("SMTP_PASSWORD", required=False)
    print()
    
    print("📅 Calendar Configuration (Optional):")
    check_env_var("GOOGLE_CALENDAR_CREDENTIALS", required=False)
    print()
    
    print("=" * 60)
    if all_good:
        print("✅ All required configurations are set!")
        print("✅ Ready to deploy to Render")
        print()
        print("Next steps:")
        print("1. git add .")
        print("2. git commit -m 'Configure for Render Background Worker'")
        print("3. git push")
        print("4. Deploy to Render using render.yaml")
        return 0
    else:
        print("❌ Some required configurations are missing!")
        print("❌ Please set missing environment variables in .env file")
        print()
        print("For Render deployment, you'll need to set these in:")
        print("Render Dashboard → Your Service → Environment")
        return 1

if __name__ == "__main__":
    sys.exit(main())
