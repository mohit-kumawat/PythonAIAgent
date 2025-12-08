#!/usr/bin/env python3
"""
Quick deployment checklist for Render Free Tier + Cron-Job.org setup
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

def check_mark(passed):
    return "✅" if passed else "❌"

def main():
    print("=" * 70)
    print("🚀 RENDER FREE TIER DEPLOYMENT CHECKLIST")
    print("=" * 70)
    print()
    
    all_checks_passed = True
    
    # 1. Environment Variables
    print("📋 1. ENVIRONMENT VARIABLES")
    print("-" * 70)
    
    required_vars = {
        "SLACK_BOT_TOKEN": os.getenv("SLACK_BOT_TOKEN"),
        "SLACK_USER_TOKEN": os.getenv("SLACK_USER_TOKEN"),
        "SLACK_BOT_USER_ID": os.getenv("SLACK_BOT_USER_ID"),
        "SLACK_USER_ID": os.getenv("SLACK_USER_ID"),
        "SLACK_CHANNELS": os.getenv("SLACK_CHANNELS"),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
    }
    
    for var, value in required_vars.items():
        has_value = bool(value and value != "xoxp-YOUR-USER-TOKEN-HERE")
        print(f"   {check_mark(has_value)} {var}")
        if not has_value:
            all_checks_passed = False
    
    print()
    
    # 2. Files Check
    print("📁 2. REQUIRED FILES")
    print("-" * 70)
    
    required_files = [
        "daemon.py",
        "health_server.py",
        "start.sh",
        "Dockerfile",
        "render.yaml",
        "requirements.txt",
    ]
    
    for file in required_files:
        exists = os.path.exists(file)
        print(f"   {check_mark(exists)} {file}")
        if not exists:
            all_checks_passed = False
    
    print()
    
    # 3. Render Service Check
    print("🌐 3. RENDER SERVICE")
    print("-" * 70)
    
    render_url = "https://pythonaiagent.onrender.com"
    
    try:
        print(f"   Testing: {render_url}/health")
        response = requests.get(f"{render_url}/health", timeout=10)
        
        if response.status_code == 200:
            print(f"   ✅ Service is LIVE and responding")
            try:
                data = response.json()
                print(f"   📊 Status: {data.get('status', 'unknown')}")
                print(f"   🕐 Timestamp: {data.get('timestamp', 'unknown')}")
            except:
                print(f"   ⚠️  Response is not JSON (might be old version)")
        else:
            print(f"   ❌ Service returned status code: {response.status_code}")
            all_checks_passed = False
            
    except requests.exceptions.ConnectionError:
        print(f"   ⚠️  Service is not reachable (might be deploying or not deployed yet)")
        print(f"   💡 Deploy your code to Render first!")
    except Exception as e:
        print(f"   ❌ Error checking service: {e}")
        all_checks_passed = False
    
    print()
    
    # 4. Cron-Job.org Check
    print("⏰ 4. CRON-JOB.ORG SETUP")
    print("-" * 70)
    print(f"   ⚠️  Manual check required:")
    print(f"   1. Go to: https://cron-job.org")
    print(f"   2. Verify job 'AI Agent' exists")
    print(f"   3. URL should be: {render_url}/health")
    print(f"   4. Schedule: Every 5 minutes")
    print(f"   5. Job should be ENABLED")
    print()
    
    # 5. Git Status
    print("📦 5. GIT STATUS")
    print("-" * 70)
    
    try:
        import subprocess
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            changes = result.stdout.strip()
            if changes:
                print(f"   ⚠️  You have uncommitted changes:")
                for line in changes.split('\n')[:5]:  # Show first 5
                    print(f"      {line}")
                if len(changes.split('\n')) > 5:
                    print(f"      ... and {len(changes.split('\n')) - 5} more")
                print()
                print(f"   💡 Run: git add . && git commit -m 'Update' && git push")
            else:
                print(f"   ✅ No uncommitted changes")
        else:
            print(f"   ⚠️  Not a git repository or git not available")
    except:
        print(f"   ⚠️  Could not check git status")
    
    print()
    
    # Summary
    print("=" * 70)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED!")
        print()
        print("🎉 Your setup is ready for deployment!")
        print()
        print("Next steps:")
        print("1. Push to GitHub: git push")
        print("2. Render will auto-deploy")
        print("3. Verify cron-job.org is pinging")
        print("4. Test by mentioning bot in Slack")
    else:
        print("❌ SOME CHECKS FAILED")
        print()
        print("Please fix the issues above before deploying.")
        print()
        print("Common fixes:")
        print("1. Update .env with missing variables")
        print("2. Get SLACK_USER_TOKEN from Slack API")
        print("3. Deploy to Render if service is not live")
    
    print("=" * 70)
    
    return 0 if all_checks_passed else 1

if __name__ == "__main__":
    sys.exit(main())
