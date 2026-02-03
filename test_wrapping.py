import unittest
from make_video_ffmpeg import add_line_breaks

class TestSubtitleWrapping(unittest.TestCase):
    def test_chinese_wrapping(self):
        # 20 Chinese characters, max 5. Should be 4 lines.
        text = "一二三四五六七八九十" * 2
        result = add_line_breaks(text, max_chars=5)
        expected = r"一二三四五\N六七八九十\N一二三四五\N六七八九十"
        self.assertEqual(result, expected)

    def test_english_wrapping(self):
        # 10 chars, max 5.
        text = "abcdefghij"
        result = add_line_breaks(text, max_chars=5)
        # a=0.5, so 10 chars = length 5. Should fit in one line if max_chars >= 5?
        # wait, 0.5 * 10 = 5.0. 
        # Loop:
        # 1. 'a', len=0.5
        # ...
        # 10. 'j', line len=4.5 + 0.5 = 5.0. <= 5. No wrap.
        self.assertEqual(result, "abcdefghij")
        
        # 11 chars = 5.5 length. Should wrap.
        text2 = "abcdefghijk"
        result2 = add_line_breaks(text2, max_chars=5)
        # 'k' makes it 5.5 > 5. Wraps 'k'.
        self.assertEqual(result2, r"abcdefghij\Nk")

    def test_mixed_wrapping(self):
        # 2 Chinese (2) + 4 English (2) = 4 length. Max 3.
        # '中' (1) -> len 1
        # '文' (1) -> len 2
        # 'a' (0.5) -> len 2.5
        # 'b' (0.5) -> len 3.0
        # 'c' (0.5) -> len 3.5 > 3. Wrap 'c'.
        text = "中文abcd"
        result = add_line_breaks(text, max_chars=3)
        self.assertEqual(result, r"中文ab\Ncd")

    def test_empty(self):
        self.assertEqual(add_line_breaks("", 10), "")

    def test_default_wrapping(self):
        # Default is 13 chars (updated for font size 70)
        # 13 chars (length 13)
        text_13 = "一" * 13
        self.assertEqual(add_line_breaks(text_13), text_13)
        
        # 14 chars (length 14) -> should wrap
        text_14 = "一" * 14
        self.assertEqual(add_line_breaks(text_14), "一"*13 + "\\N" + "一")

if __name__ == '__main__':
    unittest.main()
