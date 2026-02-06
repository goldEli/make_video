import unittest
import os
import tempfile
from make_video_ffmpeg import create_subtitle_file, add_line_breaks

class TestSubtitlePaging(unittest.TestCase):
    def setUp(self):
        self.test_file = tempfile.mktemp(suffix=".ass")
        
    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
            
    def test_short_text(self):
        # 1 line -> 1 page
        text = "Short text"
        duration = 5.0
        create_subtitle_file(text, self.test_file, duration)
        
        with open(self.test_file, 'r') as f:
            content = f.read()
            
        # Count Dialogue lines
        events = [line for line in content.splitlines() if line.startswith("Dialogue:")]
        self.assertEqual(len(events), 1)
        # Check end time is duration
        # Format H:MM:SS.cs
        # 5.0 -> 0:00:05.00
        self.assertIn("0:00:05.00", events[0])

    def test_multi_page_text(self):
        # Create text that wraps to 4 lines
        # Default max_chars=13
        # "Line1..." * 4
        # We need explicit control or trust add_line_breaks.
        # Let's trust add_line_breaks produces \N.
        
        # 4 lines of text:
        # "1111111111111" (13 chars)
        line = "一" * 13
        text = line + line + line + line
        # add_line_breaks should give "line\Nline\Nline\Nline".
        # 4 lines -> 2 pages of 2 lines.
        
        duration = 10.0
        create_subtitle_file(text, self.test_file, duration)
        
        with open(self.test_file, 'r') as f:
            content = f.read()
            
        events = [line for line in content.splitlines() if line.startswith("Dialogue:")]
        self.assertEqual(len(events), 2)
        
        # Check timestamps
        # Page 1: 2 lines. Page 2: 2 lines.
        # Equal length -> Equal duration (5.0s each).
        # Event 1: 0:00:00.00 -> 0:00:05.00
        # Event 2: 0:00:05.00 -> 0:00:10.00
        
        self.assertIn("0:00:00.00,0:00:05.00", events[0])
        self.assertIn("0:00:05.00,0:00:10.00", events[1])
        
    def test_uneven_pages(self):
        # 3 lines -> Page 1 (2 lines), Page 2 (1 line)
        line = "一" * 10
        text = line + line + line
        # 30 chars total.
        # Auto-wrapping at 13 chars:
        # Line 1: 13 chars
        # Line 2: 13 chars
        # Line 3: 4 chars
        
        # Paging (max 2 lines/page):
        # Page 1: Line 1 + Line 2 = 26 chars.
        # Page 2: Line 3 = 4 chars.
        
        # Duration distribution (Total 6.0s):
        # Page 1: (26/30) * 6.0 = 5.2s.
        # Page 2: (4/30) * 6.0 = 0.8s.
        
        duration = 6.0
        create_subtitle_file(text, self.test_file, duration)
        
        with open(self.test_file, 'r') as f:
            content = f.read()
            
        events = [line for line in content.splitlines() if line.startswith("Dialogue:")]
        self.assertEqual(len(events), 2)
        
        # Expected times:
        # Page 1: 0.0s -> 5.2s (0:00:05.20)
        # Page 2: 5.2s -> 6.0s (0:00:06.00)
        
        self.assertIn("0:00:00.00,0:00:05.20", events[0])
        self.assertIn("0:00:05.20,0:00:06.00", events[1])

if __name__ == '__main__':
    unittest.main()
