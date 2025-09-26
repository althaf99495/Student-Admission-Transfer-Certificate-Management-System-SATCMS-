from app import create_app
import socket

app = create_app()

def print_server_info():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"Serving on:")
    print(f"Local:   http://127.0.0.1:8000")
    print(f"Network: http://{local_ip}:8000")

print_server_info()
