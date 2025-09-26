# gunicorn_config.py

bind = "0.0.0.0:8000"   # Azure requires port 8000
workers = 4             # Adjust based on CPU cores
threads = 2             # Increase concurrency
worker_class = "uvicorn.workers.UvicornWorker"  # Use Uvicorn worker for async support
timeout = 120           # Handle longer-running requests
max_requests = 1000
max_requests_jitter = 100
loglevel = "info"
