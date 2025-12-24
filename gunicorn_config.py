# Gunicorn configuration file
import multiprocessing

# Worker settings
workers = 1
worker_class = 'sync'
timeout = 300  # 5 minutes - enough for AI responses
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Server mechanics
bind = '0.0.0.0:10000'
