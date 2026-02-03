#!/usr/bin/env python3
import sys
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path}")

try:
    import moviepy
    print(f"moviepy version: {moviepy.__version__}")
    
    try:
        from moviepy import editor
        print("Successfully imported moviepy.editor")
    except ImportError as e:
        print(f"Failed to import moviepy.editor: {e}")
        
except ImportError as e:
    print(f"Failed to import moviepy: {e}")
