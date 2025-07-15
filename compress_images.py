#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片压缩脚本 - 将图片压缩到指定大小以下
"""

import os
import sys
import argparse
from PIL import Image
import io

def get_file_size_mb(file_path):
    """获取文件大小（MB）"""
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)

def compress_image(input_path, output_path=None, target_size_mb=2.0, quality_start=95, quality_min=10, log_func=None):
    """压缩图片到指定大小以下
    
    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径，如果为None则覆盖原文件
        target_size_mb: 目标文件大小（MB）
        quality_start: 起始质量（1-100）
        quality_min: 最低质量（1-100）
    
    Returns:
        bool: 是否成功压缩
    """
    try:
        # 打开图片
        with Image.open(input_path) as img:
            # 保存原始EXIF信息（如果存在）
            exif_dict = None
            if hasattr(img, '_getexif') and img._getexif() is not None:
                try:
                    exif_dict = img.info.get('exif')
                except:
                    exif_dict = None
            
            # 转换为RGB模式（如果需要）
            if img.mode in ('RGBA', 'LA', 'P'):
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 如果没有指定输出路径，使用输入路径
            if output_path is None:
                output_path = input_path
            
            # 获取原始文件大小
            original_size = get_file_size_mb(input_path)
            if log_func:
                log_func(f"📊 原始文件大小: {original_size:.2f} MB")
            else:
                print(f"原始文件大小: {original_size:.2f} MB")
            
            # 如果原始文件已经小于目标大小，直接复制
            if original_size <= target_size_mb:
                if input_path != output_path:
                    save_kwargs = {'format': 'JPEG', 'quality': quality_start, 'optimize': True}
                    if exif_dict:
                        save_kwargs['exif'] = exif_dict
                    img.save(output_path, **save_kwargs)
                if log_func:
                    log_func(f"ℹ️ 文件已经小于 {target_size_mb} MB，无需压缩")
                else:
                    print(f"文件已经小于 {target_size_mb} MB，无需压缩")
                return True
            
            # 二分查找最佳质量参数
            quality_high = quality_start
            quality_low = quality_min
            best_quality = quality_min
            
            while quality_low <= quality_high:
                quality_mid = (quality_low + quality_high) // 2
                
                # 保存到内存中测试大小
                buffer = io.BytesIO()
                test_kwargs = {'format': 'JPEG', 'quality': quality_mid, 'optimize': True}
                if exif_dict:
                    test_kwargs['exif'] = exif_dict
                img.save(buffer, **test_kwargs)
                size_mb = len(buffer.getvalue()) / (1024 * 1024)
                
                if size_mb <= target_size_mb:
                    best_quality = quality_mid
                    quality_low = quality_mid + 1
                else:
                    quality_high = quality_mid - 1
            
            # 使用最佳质量保存文件，保持EXIF信息
            save_kwargs = {'format': 'JPEG', 'quality': best_quality, 'optimize': True}
            if exif_dict:
                save_kwargs['exif'] = exif_dict
            img.save(output_path, **save_kwargs)
            
            # 检查最终文件大小
            final_size = get_file_size_mb(output_path)
            if log_func:
                log_func(f"📊 压缩后文件大小: {final_size:.2f} MB (质量: {best_quality})")
            else:
                print(f"压缩后文件大小: {final_size:.2f} MB (质量: {best_quality})")
            
            if final_size <= target_size_mb:
                if log_func:
                    log_func(f"✅ 成功压缩到 {target_size_mb} MB 以下")
                else:
                    print(f"✓ 成功压缩到 {target_size_mb} MB 以下")
                return True
            else:
                if log_func:
                    log_func(f"⚠️ 警告: 即使使用最低质量({quality_min})，文件大小仍为 {final_size:.2f} MB")
                else:
                    print(f"⚠ 警告: 即使使用最低质量({quality_min})，文件大小仍为 {final_size:.2f} MB")
                return False
                
    except Exception as e:
        if log_func:
            log_func(f"❌ 压缩图片时出错: {e}")
        else:
            print(f"压缩图片时出错: {e}")
        return False

def process_directory(directory, target_size_mb=2.0, recursive=False):
    """批量处理目录中的图片"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
    processed_count = 0
    success_count = 0
    
    if recursive:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if os.path.splitext(file.lower())[1] in image_extensions:
                    file_path = os.path.join(root, file)
                    print(f"\n处理: {file_path}")
                    if compress_image(file_path, target_size_mb=target_size_mb):
                        success_count += 1
                    processed_count += 1
    else:
        for file in os.listdir(directory):
            if os.path.splitext(file.lower())[1] in image_extensions:
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    print(f"\n处理: {file_path}")
                    if compress_image(file_path, target_size_mb=target_size_mb):
                        success_count += 1
                    processed_count += 1
    
    print(f"\n处理完成: {success_count}/{processed_count} 个文件成功压缩")

def main():
    parser = argparse.ArgumentParser(description='图片压缩工具 - 将图片压缩到指定大小以下')
    parser.add_argument('input', help='输入文件或目录路径')
    parser.add_argument('-o', '--output', help='输出文件路径（仅对单个文件有效）')
    parser.add_argument('-s', '--size', type=float, default=2.0, help='目标文件大小（MB），默认2.0')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    parser.add_argument('--quality-start', type=int, default=95, help='起始质量（1-100），默认95')
    parser.add_argument('--quality-min', type=int, default=10, help='最低质量（1-100），默认10')
    
    args = parser.parse_args()
    
    # 检查输入路径是否存在
    if not os.path.exists(args.input):
        print(f"错误: 路径 '{args.input}' 不存在")
        sys.exit(1)
    
    # 验证质量参数
    if not (1 <= args.quality_start <= 100) or not (1 <= args.quality_min <= 100):
        print("错误: 质量参数必须在1-100之间")
        sys.exit(1)
    
    if args.quality_min > args.quality_start:
        print("错误: 最低质量不能大于起始质量")
        sys.exit(1)
    
    print(f"目标大小: {args.size} MB")
    print(f"质量范围: {args.quality_min} - {args.quality_start}")
    
    if os.path.isfile(args.input):
        # 处理单个文件
        print(f"\n处理单个文件: {args.input}")
        success = compress_image(
            args.input, 
            args.output, 
            args.size, 
            args.quality_start, 
            args.quality_min
        )
        if success:
            print("\n✓ 文件处理完成")
        else:
            print("\n✗ 文件处理失败")
            sys.exit(1)
    
    elif os.path.isdir(args.input):
        # 处理目录
        print(f"\n处理目录: {args.input}")
        if args.output:
            print("警告: 处理目录时忽略 --output 参数")
        process_directory(args.input, args.size, args.recursive)
    
    else:
        print(f"错误: '{args.input}' 既不是文件也不是目录")
        sys.exit(1)

if __name__ == '__main__':
    main()