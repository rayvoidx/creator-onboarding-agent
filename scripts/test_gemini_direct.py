#!/usr/bin/env python3
"""Direct test for Gemini API."""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key loaded: {api_key[:20]}...{api_key[-10:]}")
print(f"API Key length: {len(api_key)}")

genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.0-flash")
response = model.generate_content("Say 'OK' only")
print(f"Response: {response.text}")
