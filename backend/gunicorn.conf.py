import os

# Loaded automatically by gunicorn from the working directory, whatever start command the platform uses.
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 2
threads = 4
timeout = 120  # a plan can wait ~60 s on slow ORS calls; gunicorn's default 30 s would kill it
