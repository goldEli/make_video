from make_video_ffmpeg import generate_zoompan_filter, ZOOM_INPUT_W, ZOOM_INPUT_H

# Test filters
duration = 5.0
intensity = 0.6
fps = 25

# Generate multiple filters to likely hit all 3 types (Zoom In, Zoom Out, Pan)
for i in range(5):
    filt = generate_zoompan_filter(
        duration, 
        intensity, 
        fps,
        ZOOM_INPUT_W,
        ZOOM_INPUT_H
    )
    print(f"Filter {i} (len {len(filt)}): {filt[:100]}...")
    
    # Assert basic structure
    assert "zoompan=" in filt
    assert "z='" in filt
    assert "x='" in filt
    assert "y='" in filt
    assert f"d={int(duration*fps)}" in filt
    
    # Check for interpolation format logic (simple linear interpolation)
    # The new logic returns expressions like "1.0+(1.3-1.0)*on/125"
    # We can check for the presence of "*on/" which indicates our linear formula
    assert "*on/" in filt

print("Verification successful!")
