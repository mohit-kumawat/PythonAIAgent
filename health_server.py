"""
Health check server for Render Free Tier + cron-job.org integration.
When cron-job.org pings this endpoint, it triggers a Slack check.
This keeps the service alive AND makes it check Slack every 5 minutes.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import json
import subprocess
from datetime import datetime

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Respond to health checks and trigger actions"""
        if self.path == '/' or self.path == '/health':
            # Respond immediately
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "alive",
                "service": "The Real PM Agent",
                "timestamp": datetime.now().isoformat(),
                "message": "Service is running. Cron ping received."
            }
            
            self.wfile.write(json.dumps(response).encode())
            
            # Log the ping
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Health check pinged - Service kept alive")
            
        elif self.path == '/trigger':
            # Manual trigger endpoint (optional)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "triggered",
                "message": "Manual check triggered"
            }
            
            self.wfile.write(json.dumps(response).encode())
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔔 Manual trigger received")
            
        elif self.path == '/status':
            # Status endpoint
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Try to read status from server_state
            try:
                status_file = 'server_state/status.json'
                if os.path.exists(status_file):
                    with open(status_file, 'r') as f:
                        status_data = json.load(f)
                else:
                    status_data = {"status": "running", "detail": "No status file yet"}
            except:
                status_data = {"status": "running", "detail": "Status unavailable"}
            
            self.wfile.write(json.dumps(status_data).encode())
            
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def do_POST(self):
        """Handle Slack Events API webhooks for instant response"""
        if self.path == '/slack/events':
            try:
                # Read the request body
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                event_data = json.loads(body.decode('utf-8'))
                
                # 1. Handle Slack URL Verification (one-time setup)
                if event_data.get("type") == "url_verification":
                    challenge = event_data.get("challenge", "")
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(challenge.encode())
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Slack URL verification successful")
                    return
                
                # 2. Handle Event Callbacks (app_mention, message, etc.)
                if event_data.get("type") == "event_callback":
                    event = event_data.get("event", {})
                    event_type = event.get("type")
                    
                    # Respond to Slack immediately (required within 3 seconds)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": True}).encode())
                    
                    # Log the event
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔔 Slack event received: {event_type}")
                    
                    # Handle app_mention events (instant response!)
                    if event_type == "app_mention":
                        channel_id = event.get("channel")
                        user_id = event.get("user")
                        text = event.get("text", "")
                        
                        print(f"   📨 Mention from user {user_id} in channel {channel_id}")
                        print(f"   💬 Message: {text[:100]}...")
                        
                        # Trigger immediate check for this specific channel
                        # Run in a separate thread to avoid blocking the webhook response
                        import threading
                        from daemon import check_mentions_job
                        from client_manager import ClientManager
                        
                        def run_immediate_check():
                            try:
                                manager = ClientManager()
                                check_mentions_job(manager, [channel_id])
                            except Exception as e:
                                print(f"Error in immediate check: {e}")
                        
                        thread = threading.Thread(target=run_immediate_check, daemon=True)
                        thread.start()
                        print(f"   ⚡ Triggered immediate analysis for channel {channel_id}")
                    
                    return
                
                # Default response for other event types
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode())
                
            except Exception as e:
                print(f"Error handling Slack event: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        """Suppress default logging to reduce noise"""
        pass

def start_health_server(port=10000):
    """Start a simple HTTP server for health checks"""
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Health check server running on port {port}")
    print(f"📍 Endpoints:")
    print(f"   - GET  /health        - Health check (for cron-job.org)")
    print(f"   - GET  /status        - Service status")
    print(f"   - GET  /trigger       - Manual trigger")
    print(f"   - POST /slack/events  - Slack Events API webhook (INSTANT RESPONSE)")
    print(f"\n💡 To enable instant responses:")
    print(f"   1. Go to https://api.slack.com/apps")
    print(f"   2. Select your app → Event Subscriptions")
    print(f"   3. Enable Events and set Request URL to: https://your-domain.com/slack/events")
    print(f"   4. Subscribe to 'app_mention' event")
    server.serve_forever()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    start_health_server(port)
