"""
Simple HTTP health check server for Render Web Service compatibility.
Runs alongside the daemon to keep the service alive.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Respond to health checks"""
        if self.path == '/' or self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'The Real PM Agent is running!')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

def start_health_server(port=10000):
    """Start a simple HTTP server for health checks"""
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Health check server running on port {port}")
    server.serve_forever()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    start_health_server(port)
