#!/usr/bin/env python3
import json
import os
import random
import tempfile
import subprocess
import requests

# 全局效果控制参数
# 全局效果控制参数
EFFECT_INTENSITY = 0.3  # 效果强度 (0.0 - 1.0)
FPS = 25                # 视频帧率
ZOOM_INPUT_W = 2160     # Zoompan 输入宽度 (2x 1080)
ZOOM_INPUT_H = 3840     # Zoompan 输入高度 (2x 1920)

def download_resource(url, output_path):
    """下载资源文件"""
    print(f"下载资源: {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"下载完成: {output_path}")

def get_audio_duration(audio_path):
    """获取音频文件的实际时长"""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())

def create_video_segment(image_path, audio_path, subtitle_text, duration, output_path, index):
    """使用 FFmpeg 创建单个视频片段"""
    print(f"创建视频片段 {index+1}...")
    
    # 获取音频实际时长
    try:
        actual_duration = get_audio_duration(audio_path)
        # 使用实际时长，避免时长不匹配问题
        duration = min(duration, actual_duration)
        print(f"使用音频实际时长: {duration:.2f}秒")
    except Exception as e:
        print(f"获取音频时长失败，使用原始时长: {e}")
    
    # 生成随机动画效果
    zoompan_filter = generate_zoompan_filter(
        duration, 
        EFFECT_INTENSITY, 
        FPS,
        ZOOM_INPUT_W,
        ZOOM_INPUT_H
    )
    
    # 创建字幕文件
    subtitle_file = os.path.join(os.path.dirname(output_path), f"subtitle_{index}.ass")
    create_subtitle_file(subtitle_text, subtitle_file, duration)
    
    # 构建 FFmpeg 命令
    # 关键点：
    # 1. 先 scale 到 2160x3840 (1080x2倍)，为 zoompan 提供更高分辨率的输入，减少模糊
    # 2. 应用 zoompan 动画并输出 1080x1920
    # 3. 最后叠加字幕
    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-t', str(duration), '-i', image_path,
        '-i', audio_path,
        '-vf', f"scale={ZOOM_INPUT_W}:{ZOOM_INPUT_H},{zoompan_filter},ass={subtitle_file}",
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
        '-c:a', 'aac', '-b:a', '128k',
        '-shortest',
        output_path
    ]
    
    # 执行命令
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg 错误: {result.stderr}")
            raise Exception(f"FFmpeg 执行失败: {result.stderr}")
        print(f"视频片段 {index+1} 创建完成")
    except Exception as e:
        print(f"创建视频片段失败: {e}")
        raise

def generate_zoompan_filter(duration, intensity, fps, width, height):
    """
    生成单次效果的 zoompan 滤镜字符串 (Zoom In, Zoom Out, 或 Pan)
    duration: 片段时长（秒）
    intensity: 效果强度 (0.0 - 1.0)
    width, height: 输入图像的分辨率
    """
    total_frames = int(duration * fps)
    if total_frames <= 0: return f"scale=1080:1920"
    
    # 效果类型: 0=Zoom In, 1=Zoom Out, 2=Pan
    effect_type = random.choice([0, 1, 2])
    
    # 参数范围
    # Zoom range: 1.0 to 1.3~1.5
    min_zoom = 1.0
    max_zoom = 1.0 + (0.5 * intensity)
    
    keyframes = []
    
    if effect_type == 0:  # Zoom In
        # Start at 1.0, End at ~1.3
        z_start = min_zoom
        z_end = random.uniform(min_zoom + 0.1, max_zoom)
        # Center or slight offset focus
        x_center = width / 2
        y_center = height / 2
        # Start x,y (at zoom 1) must be 0,0
        # End x,y should be roughly centered relative to the crop
        # x = (width/2) - (view_w/2). view_w = width/z
        # x = width/2 - width/(2*z) = width * (1 - 1/z) / 2
        
        # We start at full view (x=0, y=0, z=1)
        k1 = {'f': 0, 'z': z_start, 'x': 0, 'y': 0}
        
        # End view
        # Randomize target center slightly? For now strict center zoom in
        x_end = width * (1 - 1/z_end) / 2
        y_end = height * (1 - 1/z_end) / 2
        
        k2 = {'f': total_frames, 'z': z_end, 'x': x_end, 'y': y_end}
        
    elif effect_type == 1:  # Zoom Out
        # Start at ~1.3, End at 1.0
        z_start = random.uniform(min_zoom + 0.1, max_zoom)
        z_end = min_zoom
        
        x_start = width * (1 - 1/z_start) / 2
        y_start = height * (1 - 1/z_start) / 2
        
        k1 = {'f': 0, 'z': z_start, 'x': x_start, 'y': y_start}
        k2 = {'f': total_frames, 'z': z_end, 'x': 0, 'y': 0}
        
    else: # Pan
        # Constant zoom level, move from A to B
        z_val = random.uniform(min_zoom + 0.2, max_zoom)
        
        # Max movement range
        max_x = width * (1 - 1/z_val)
        max_y = height * (1 - 1/z_val)
        
        # Random start and end points
        x1 = random.uniform(0, max_x)
        y1 = random.uniform(0, max_y)
        
        x2 = random.uniform(0, max_x)
        y2 = random.uniform(0, max_y)
        
        k1 = {'f': 0, 'z': z_val, 'x': x1, 'y': y1}
        k2 = {'f': total_frames, 'z': z_val, 'x': x2, 'y': y2}

    keyframes = [k1, k2]

    def get_interp_expr(attr):
        f1, f2 = keyframes[0]['f'], keyframes[1]['f']
        v1, v2 = keyframes[0][attr], keyframes[1][attr]
        # Linear interpolation
        # expr = v1 + (v2-v1) * on / total_frames
        return f"{v1}+({v2}-{v1})*on/{total_frames}"

    z_expr = get_interp_expr('z')
    x_expr = get_interp_expr('x')
    y_expr = get_interp_expr('y')
    
    return f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={total_frames}:s=1080x1920:fps={fps}"

def add_line_breaks(text, max_chars=13):
    """
    主要针对中文的自动换行，也兼容英文
    max_chars: 每行大约多少个中文字符
    1080p 竖屏, margins=60*2=120, usable=960. font=70. 960/70 ~= 13.7. 
    Suggested max_chars=13.
    """
    lines = []
    current_line = ""
    current_length = 0
    
    # 遍历每个字符
    for char in text:
        # 中文字符算1，其他(如英文、数字、标点)算0.5
        char_len = 1 if ord(char) > 127 else 0.5
        
        # 如果加上当前字符会超出限制（且当前行不为空），则换行
        if current_length + char_len > max_chars and current_line:
            lines.append(current_line)
            current_line = char
            current_length = char_len
        else:
            current_line += char
            current_length += char_len
            
    if current_line:
        lines.append(current_line)
        
    # ASS格式换行符是 \N
    return '\\N'.join(lines)

def create_subtitle_file(text, output_path, duration):
    """创建 ASS 字幕文件 (支持分页，每页最多2行)"""
    
    # 添加换行符
    wrapped_text = add_line_breaks(text)
    
    # Split into lines (handling the \N delimiter)
    lines = wrapped_text.split('\\N')
    
    # Chunk into pages of Max 2 lines
    pages = []
    current_page = []
    for line in lines:
        current_page.append(line)
        if len(current_page) == 2:
            pages.append(current_page)
            current_page = []
    if current_page:
        pages.append(current_page)
        
    # Calculate durations
    # Total chars to distribute duration
    total_chars = sum(len(line) for page in pages for line in page)
    if total_chars == 0: total_chars = 1 # Avoid division by zero
    
    ass_header = f"""[Script Info]
; Script generated by make_video_ffmpeg.py
Title: Subtitle
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Unicode MS,70,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,2,2,60,60,350,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events_str = ""
    current_time = 0.0
    
    def format_time(t):
        """Format seconds to H:MM:SS.cs"""
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        cs = int((t * 100) % 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    for i, page in enumerate(pages):
        page_text = '\\N'.join(page)
        page_chars = sum(len(line) for line in page)
        
        # Calculate duration for this page
        # For the last page, we use the remaining time to ensure we match total duration exactly
        if i == len(pages) - 1:
            page_duration = duration - current_time
        else:
            page_duration = (page_chars / total_chars) * duration
            
        start_time = current_time
        end_time = current_time + page_duration
        
        # Precision clamping (start shouldn't exceed end)
        if start_time > end_time: start_time = end_time
        
        start_str = format_time(start_time)
        end_str = format_time(end_time)
        
        events_str += f"Dialogue: 0,{start_str},{end_str},Default,,60,60,350,,{page_text}\n"
        
        current_time = end_time

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_header + events_str)

def concatenate_videos(segment_files, output_path):
    """合并多个视频片段"""
    print("合并视频片段...")
    
    # 创建文件列表
    list_file = os.path.join(os.path.dirname(output_path), "filelist.txt")
    with open(list_file, 'w') as f:
        for file in segment_files:
            f.write(f"file '{file}'\n")
    
    # 构建 FFmpeg 命令
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0', '-i', list_file,
        '-c', 'copy',
        output_path
    ]
    
    # 执行命令
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    print("视频合并完成")

def main():
    """主函数"""
    # 读取 input.json
    with open('input.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 验证数据结构
    list_items = data.get('list', [])
    audio_list = data.get('audio_list', [])
    duration_list = data.get('duration_list', [])
    image_list = data.get('image_list', [])
    
    # 检查列表长度是否一致
    if not all(len(lst) == len(list_items) for lst in [audio_list, duration_list, image_list]):
        raise ValueError("所有列表长度必须一致")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        segment_files = []
        
        # 处理每个片段
        for i, (item, audio_url, duration_ms, image_url) in enumerate(zip(
            list_items, audio_list, duration_list, image_list
        )):
            print(f"处理片段 {i+1}/{len(list_items)}")
            
            # 转换时长为秒
            duration = duration_ms / 1000
            
            # 下载资源
            audio_path = os.path.join(temp_dir, f"audio_{i}.mp3")
            image_path = os.path.join(temp_dir, f"image_{i}.jpg")
            segment_path = os.path.join(temp_dir, f"segment_{i}.mp4")
            
            download_resource(audio_url, audio_path)
            download_resource(image_url, image_path)
            
            # 创建视频片段
            create_video_segment(image_path, audio_path, item['cap'], duration, segment_path, i)
            segment_files.append(segment_path)
        
        # 拼接所有片段
        output_path = "output.mp4"
        concatenate_videos(segment_files, output_path)
        
        print(f"视频生成完成！输出文件: {output_path}")

if __name__ == "__main__":
    main()
