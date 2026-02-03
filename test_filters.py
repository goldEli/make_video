from make_video_ffmpeg import generate_zoompan_filter, ZOOM_INPUT_W, ZOOM_INPUT_H

# Test filter generation
duration = 5.0
intensity = 0.6
frequency = 0.5
fps = 25

filt = generate_zoompan_filter(
    duration, 
    intensity, 
    frequency, 
    fps,
    ZOOM_INPUT_W,
    ZOOM_INPUT_H
)
print(f"Generated filter (length {len(filt)}):")
print(filt[:200] + "...")

# Check for presence of key identifiers
assert "zoompan=" in filt
assert "z='if(between(on" in filt
assert "x='if(between(on" in filt
assert "y='if(between(on" in filt
assert f"d={int(duration*fps)}" in filt

print("Verification successful!")
