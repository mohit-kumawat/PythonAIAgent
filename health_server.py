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
    
    def log_message(self, format, *args):
        """Suppress default logging to reduce noise"""
        pass

def start_health_server(port=10000):
    """Start a simple HTTP server for health checks"""
    
    # Start the Daemon in a background thread if channels are configured
    import threading
    from daemon import start_daemon
    
    # Get channels from env var (comma separated) or default
    channels_env = os.environ.get("SLACK_CHANNELS", "")
    if channels_env:
        channel_ids = [c.strip() for c in channels_env.split(",") if c.strip()]
    else:
        # Fallback for now if env not set, but better to log warning
        print("⚠️ WARNING: SLACK_CHANNELS env var not set! Daemon might not monitor anything.")
        # Try to find a default from typical usage or just use C08JF2UFCR1
        channel_ids = ["C08JF2UFCR1"] 
        
    print(f"🚀 Starting Daemon for channels: {channel_ids}")
    daemon_thread = threading.Thread(target=start_daemon, args=(channel_ids,), daemon=True)
    daemon_thread.start()

    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Health check server running on port {port}")
    print(f"📍 Endpoints:")
    print(f"   - GET /health - Health check (for cron-job.org)")
    print(f"   - GET /status - Service status")
    print(f"   - GET /trigger - Manual trigger")
    server.serve_forever()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    start_health_server(port)
