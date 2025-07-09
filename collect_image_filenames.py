#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
收集指定目录下的图片文件名并写入文本文件
"""

import os
import glob
import sys

def collect_image_filenames(target_dir='.'):
    """收集指定目录下的图片文件名"""
    # 常见的图片文件扩展名
    image_extensions = [
        '*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', 
        '*.tiff', '*.tif', '*.webp', '*.svg', '*.ico',
        '*.JPG', '*.JPEG', '*.PNG', '*.GIF', '*.BMP',
        '*.TIFF', '*.TIF', '*.WEBP', '*.SVG', '*.ICO',
        '*.heic', '*.HEIC', '*.raw', '*.RAW'
    ]
    
    image_files = []
    
    # 切换到目标目录
    original_dir = os.getcwd()
    try:
        os.chdir(target_dir)
        # 遍历所有图片扩展名，查找匹配的文件
        for extension in image_extensions:
            files = glob.glob(extension)
            image_files.extend(files)
    finally:
        os.chdir(original_dir)
    
    # 去重并排序
    image_files = sorted(list(set(image_files)))
    
    return image_files

def write_to_text_file(image_files, target_dir='.', remove_extension=True, output_file='image_filenames.txt'):
    """将图片文件名写入文本文件"""
    # 构建输出文件的完整路径
    output_path = os.path.join(target_dir, output_file)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for filename in image_files:
                if remove_extension:
                    # 去掉文件扩展名
                    name_without_ext = os.path.splitext(filename)[0]
                    f.write(name_without_ext + '\n')
                else:
                    f.write(filename + '\n')
        print(f"成功将 {len(image_files)} 个图片文件名写入 {output_path}")
        return True
    except Exception as e:
        print(f"写入文件时出错: {e}")
        return False

def main():
    """主函数"""
    # 获取目标目录参数
    target_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    # 检查目录是否存在
    if not os.path.exists(target_dir):
        print(f"错误：目录 '{target_dir}' 不存在")
        sys.exit(1)
    
    if not os.path.isdir(target_dir):
        print(f"错误：'{target_dir}' 不是一个目录")
        sys.exit(1)
    
    print(f"正在收集目录 '{target_dir}' 下的图片文件名...")
    
    # 收集图片文件名
    image_files = collect_image_filenames(target_dir)
    
    if image_files:
        print(f"找到 {len(image_files)} 个图片文件:")
        for filename in image_files:
            print(f"  - {filename}")
        
        # 写入文本文件
        write_to_text_file(image_files, target_dir)
    else:
        print(f"目录 '{target_dir}' 下没有找到图片文件")
        # 仍然创建一个空的文本文件
        write_to_text_file([], target_dir, 'image_filenames.txt')

if __name__ == '__main__':
    main()