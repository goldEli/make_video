#!/usr/bin/env python3
from moviepy import TextClip

# Print TextClip __init__ signature
import inspect
print(inspect.signature(TextClip.__init__))

# Test creating a simple TextClip
try:
    clip = TextClip("Test", fontsize=48, color='white', font='Arial')
    print("TextClip created successfully")
except Exception as e:
    print(f"Error creating TextClip: {e}")
