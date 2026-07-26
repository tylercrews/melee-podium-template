"""Passenger entry point for the cPanel deployment."""

import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT))

from app import app as application
