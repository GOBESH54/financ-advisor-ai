#!/usr/bin/env python3
"""Celery worker for background task processing"""

import os
import sys
from app import app, task_manager

# Make the celery instance available
celery = task_manager.celery

if __name__ == '__main__':
    # Start Celery worker
    celery.start()