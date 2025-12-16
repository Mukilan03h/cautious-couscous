"""Run Celery worker and beat scheduler for Windows.

Usage: python scripts/run_celery.py
"""
import subprocess
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("Starting Celery worker and beat scheduler...")
    
    # Start worker process
    worker = subprocess.Popen([
        sys.executable, "-m", "celery",
        "-A", "esa.background.celery.apps.primary",
        "worker", "--loglevel=info", "--pool=solo"
    ])
    
    # Start beat process
    beat = subprocess.Popen([
        sys.executable, "-m", "celery",
        "-A", "esa.background.celery.apps.beat",
        "beat", "--loglevel=info"
    ])
    
    print("Celery worker PID:", worker.pid)
    print("Celery beat PID:", beat.pid)
    print("Press Ctrl+C to stop both...")
    
    try:
        worker.wait()
    except KeyboardInterrupt:
        print("\nStopping Celery...")
        worker.terminate()
        beat.terminate()
        worker.wait()
        beat.wait()
        print("Stopped.")

if __name__ == "__main__":
    main()
