import os

# Read PORT dynamically from cloud environment (Render, Railway, Heroku)
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Worker processes and timeout
workers = 2
threads = 2
timeout = 120
