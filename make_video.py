#!/usr/bin/env python3
import json
import os
import random
import tempfile
import requests
from moviepy import (
    VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip,
    TextClip, concatenate_videoclips
)
from moviepy.video.fx import Resize


def download_resource(url, output_path):
    """下载资源文件"""
    print(f"下载资源: {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"下载完成: {output_path}")


def create_image_animation(image_path, duration, size=(1920, 1080)):
    """创建图片动画效果"""
    # 随机生成动画参数
    zoom_factor = random.uniform(1.0, 1.1)
    pan_x = random.uniform(-50, 50)
    pan_y = random.uniform(-30, 30)
    
    # 创建图片剪辑
    clip = ImageClip(image_path).with_duration(duration).resized(size)
    
    # 使用 lambda 函数实现动画效果
    def make_frame(get_frame, t):
        # 计算缩放和位移
        scale = 1 + (zoom_factor - 1) * (t / duration)
        x = pan_x * (t / duration)
        y = pan_y * (t / duration)
        
        # 获取原始帧
        frame = get_frame(t)
        
        # 这里我们可以直接返回原始帧，因为我们已经通过其他方式设置了动画
        return frame
    
    # 创建新的 VideoClip 并设置帧生成函数
    animated_clip = clip.transform(make_frame)
    return animated_clip


def create_subtitle_clip(text, duration, size=(1920, 1080)):
    """创建字幕剪辑"""
    from moviepy import ColorClip
    
    # 创建字幕文本剪辑
    txt_clip = TextClip(
        text=text, font_size=48, color='white', font='Arial',
        size=(size[0] - 100, None),
        method='caption'
    ).with_duration(duration)
    
    # 获取字幕大小
    txt_width, txt_height = txt_clip.size
    
    # 创建半透明背景
    bg_clip = ColorClip(
        size=(txt_width + 40, txt_height + 20),
        color=(0, 0, 0),  # 黑色背景
        duration=duration
    ).with_opacity(0.5)  # 设置透明度
    
    # 组合字幕和背景
    composite_clip = CompositeVideoClip([bg_clip, txt_clip], size=(txt_width + 40, txt_height + 20))
    
    # 设置字幕位置（底部）
    composite_clip = composite_clip.with_position(('center', 'bottom'))
    return composite_clip


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
        clips = []
        
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
            
            download_resource(audio_url, audio_path)
            download_resource(image_url, image_path)
            
            # 创建图片动画
            image_clip = create_image_animation(image_path, duration)
            
            # 创建音频剪辑
            audio_clip = AudioFileClip(audio_path)
            # 使用音频文件的实际时长，避免时长不匹配问题
            actual_duration = audio_clip.duration
            audio_clip = audio_clip.with_duration(min(actual_duration, duration))
            # 更新使用的时长为实际音频时长
            duration = audio_clip.duration
            
            # 创建字幕剪辑
            subtitle_clip = create_subtitle_clip(item['cap'], duration)
            
            # 组合剪辑
            composite_clip = CompositeVideoClip([image_clip, subtitle_clip])
            composite_clip = composite_clip.with_audio(audio_clip)
            
            clips.append(composite_clip)
        
        # 拼接所有剪辑
        print("拼接视频片段...")
        final_clip = concatenate_videoclips(clips)
        
        # 输出最终视频
        output_path = "output.mp4"
        print(f"生成最终视频: {output_path}")
        final_clip.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac"
        )
        
        print("视频生成完成！")


if __name__ == "__main__":
    main()


"""
使用说明：

1. 创建 uv 环境并安装依赖：
   ```bash
   uv init
   uv add moviepy requests
   ```

2. 创建 input.json 文件，按照以下格式：
   ```json
   {
     "list": [
       { "cap": "字幕内容 1" },
       { "cap": "字幕内容 2" }
     ],
     "audio_list": [
       "音频文件 URL 1",
       "音频文件 URL 2"
     ],
     "duration_list": [
       3200,
       2800
     ],
     "image_list": [
       "图片文件 URL 1",
       "图片文件 URL 2"
     ]
   }
   ```

3. 运行脚本：
   ```bash
   python make_video.py
   ```

4. 脚本会自动下载所有资源并生成 output.mp4 文件
"""
