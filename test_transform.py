#!/usr/bin/env python3
from moviepy import ImageClip
import numpy as np

# Create a simple test image using numpy
img = np.zeros((100, 100, 3), dtype=np.uint8)
clip = ImageClip(img)
print(f"ImageClip methods: {[method for method in dir(clip) if not method.startswith('_')]}")
print(f"Has transform method: {'transform' in dir(clip)}")
print(f"Has fl method: {'fl' in dir(clip)}")
