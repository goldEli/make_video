#!/usr/bin/env python3
import json
import os
import random
import tempfile
import subprocess
import requests

# 全局效果控制参数
EFFECT_INTENSITY = 0.6  # 效果强度 (0.0 - 1.0)
EFFECT_FREQUENCY = 0.5  # 效果频率 (每秒关键帧数)
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
        EFFECT_FREQUENCY, 
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

def generate_zoompan_filter(duration, intensity, frequency, fps, width, height):
    """
    生成随机关键帧的 zoompan 滤镜字符串
    duration: 片段时长（秒）
    intensity: 缩放/平移强度 (0.0 - 1.0)
    frequency: 关键帧频率 (Hz)
    width, height: 输入图像的分辨率（用于计算平移限制）
    """
    total_frames = int(duration * fps)
    if total_frames <= 0: return "scale=1080:1920"
    
    # 基础缩放 1.0 - 1.3 (基于intensity)
    base_zoom = 1.0
    # 最大缩放，不超过 1.5 倍 (针对 2x 输入图，实际 zoompan 内部 zoom=1 是输出尺寸/输入尺寸?)
    # FFmpeg zoompan zoom=1 意味着显示区域大小等于输出大小(1080x1920)。
    # 如果输入是 2160x3840，那么 zoom=1 时，显示区域是 1080x1920 (即裁剪出 1080x1920 的区域)。
    # 不，zoompan 的 zoom 值是相对于 "输出尺寸" 的视窗大小吗？
    # Doc: "Zoom is the zoom factor. verify the range of the zoom factor is [1, 10]."
    # Zoom=1 means the crop size is same as input size? No.
    # Actually zoompan works on the input image. 
    # Let's assume input WxH. Output wxh.
    # zoom=1 means we see the whole WxH image scaled down to wxh.
    # zoom=2 means we see half the WxH image scaled to wxh.
    
    # However, to avoid upscale blur, we upscaled input to 2x. 
    # So if we want to show "full image", we need to see the full 2160x3840.
    # But filters like zoompan often normalize coordinates.
    # Actually, simpler logic:
    # 1. We have 2160x3840 input.
    # 2. We want output 1080x1920.
    # 3. If "zoom=1" in zoompan typically means "show full input frame scaled to output", 
    #    then that's fine.
    #    But if we want to zoom IN, we increase zoom.
    
    # Range:
    min_zoom = 1.0
    max_zoom = 1.0 + (0.5 * intensity) # Max 1.5x zoom
    
    # 生成关键帧
    num_keyframes = max(2, int(duration * frequency) + 1)
    keyframes = []
    for i in range(num_keyframes):
        frame = int(i * total_frames / (num_keyframes - 1))
        z = random.uniform(min_zoom, max_zoom)
        
        # 计算 (x, y) 坐标
        # zoompan 的 x,y 是视窗左上角的坐标。
        # 视窗大小 (vw, vh) = (InputW / z, InputH / z) ?? 
        # No, zoompan manual says: zoom=1 displays the whole input frame.
        # Let's verify behavior. Usually:
        # x, y range is approx: InputW * (1 - 1/z) and InputH * (1 - 1/z).
        # Because we want to keep the aspect ratio 9:16.
        
        max_x = width * (1 - 1/z)
        max_y = height * (1 - 1/z)
        
        x = random.uniform(0, max_x)
        y = random.uniform(0, max_y)
        
        keyframes.append({'f': frame, 'z': z, 'x': x, 'y': y})

    def get_interp_expr(attr):
        expr = f"{keyframes[0][attr]}"
        for i in range(len(keyframes) - 1):
            f1, f2 = keyframes[i]['f'], keyframes[i+1]['f']
            v1, v2 = keyframes[i][attr], keyframes[i+1][attr]
            if f1 == f2: continue
            # 线性插值
            interp = f"({v1}+({v2}-{v1})*(on-{f1})/({f2}-{f1}))"
            expr = f"if(between(on,{f1},{f2}),{interp},{expr})"
        return expr

    z_expr = get_interp_expr('z')
    x_expr = get_interp_expr('x')
    y_expr = get_interp_expr('y')
    
    # s=1080x1920 means the output resolution.
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
    """创建 ASS 字幕文件"""
    
    # 添加换行符
    wrapped_text = add_line_breaks(text)
    
    # 为竖屏 1080x1920 调整 ASS 配置
    ass_content = f"""[Script Info]
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
Dialogue: 0,0:00:00.00,0:{int(duration//60):02d}:{int(duration%60):02d}.00,Default,,60,60,350,,{wrapped_text}
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

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
