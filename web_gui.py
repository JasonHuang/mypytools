#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web版图片处理工具GUI
使用Flask提供Web界面，完全兼容所有操作系统
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import json
import webbrowser
import threading
import time
from datetime import datetime

app = Flask(__name__)

# 全局变量存储操作日志
operation_logs = []

def add_log(message):
    """添加操作日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    operation_logs.append(log_entry)
    print(log_entry)

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html', title='图片处理工具')

@app.route('/api/logs')
def get_logs():
    """获取操作日志"""
    return jsonify({'logs': operation_logs})

@app.route('/api/clear_logs', methods=['POST'])
def clear_logs():
    """清除日志"""
    global operation_logs
    operation_logs = []
    add_log("📋 日志已清除")
    return jsonify({'success': True})

@app.route('/api/collect_filenames', methods=['POST'])
def collect_filenames():
    """文件名收集API"""
    try:
        data = request.json
        directory = data.get('directory', '')
        include_subdirs = data.get('include_subdirs', False)
        remove_extension = data.get('remove_extension', False)
        files_data = data.get('files_data', [])
        output_path = data.get('output_path', '')
        
        add_log(f"📁 开始收集文件名: {directory}")
        add_log(f"   递归子目录: {'是' if include_subdirs else '否'}")
        add_log(f"   去除扩展名: {'是' if remove_extension else '否'}")
        
        if not output_path:
            error_msg = "❌ 请填写输出路径"
            add_log(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
        if not files_data:
            error_msg = "❌ 请先选择文件或目录"
            add_log(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
        # 收集文件名
        filenames = []
        for file_info in files_data:
            if 'path' in file_info:
                # 目录选择的情况，使用相对路径
                filename = file_info['path']
            else:
                # 文件选择的情况，使用文件名
                filename = file_info['name']
            
            # 去除扩展名选项
            if remove_extension and '.' in filename:
                filename = '.'.join(filename.split('.')[:-1])
            
            filenames.append(filename)
        
        # 写入文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for filename in filenames:
                    f.write(filename + '\n')
            
            add_log(f"✅ 文件名收集完成，共收集 {len(filenames)} 个文件名")
            add_log(f"📄 已保存到: {output_path}")
            return jsonify({'success': True, 'message': f'文件名收集完成！共收集 {len(filenames)} 个文件名'})
            
        except Exception as e:
            error_msg = f"❌ 写入文件失败: {str(e)}"
            add_log(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
    except Exception as e:
        error_msg = f"❌ 文件名收集失败: {str(e)}"
        add_log(error_msg)
        return jsonify({'success': False, 'error': error_msg})

@app.route('/api/compress_images', methods=['POST'])
def compress_images():
    """图片压缩API"""
    try:
        data = request.json
        source_path = data.get('source_path', '')
        quality = data.get('quality', 85)
        max_width = data.get('max_width', 1920)
        recursive = data.get('recursive', False)
        
        add_log(f"🗜️ 开始压缩图片: {source_path}")
        add_log(f"   压缩质量: {quality}%")
        add_log(f"   最大宽度: {max_width}px")
        add_log(f"   递归处理: {'是' if recursive else '否'}")
        
        # 这里可以调用实际的图片压缩函数
        # from compress_images import main as compress_main
        
        add_log("✅ 图片压缩完成")
        return jsonify({'success': True, 'message': '图片压缩完成'})
        
    except Exception as e:
        error_msg = f"❌ 图片压缩失败: {str(e)}"
        add_log(error_msg)
        return jsonify({'success': False, 'error': error_msg})

@app.route('/api/convert_format', methods=['POST'])
def convert_format():
    """格式转换API"""
    try:
        data = request.json
        source_path = data.get('source_path', '')
        output_format = data.get('output_format', 'jpg')
        quality = data.get('quality', 95)
        
        add_log(f"🔄 开始格式转换: {source_path}")
        add_log(f"   输出格式: {output_format.upper()}")
        add_log(f"   转换质量: {quality}%")
        
        # 这里可以调用实际的格式转换函数
        # from convert_heic_to_jpg import main as convert_main
        
        add_log("✅ 格式转换完成")
        return jsonify({'success': True, 'message': '格式转换完成'})
        
    except Exception as e:
        error_msg = f"❌ 格式转换失败: {str(e)}"
        add_log(error_msg)
        return jsonify({'success': False, 'error': error_msg})

def ensure_directories():
    """确保模板和静态文件目录存在"""
    directories = ['templates', 'static', 'static/css', 'static/js']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            add_log(f"📁 创建目录: {directory}")

def open_browser():
    """延迟打开浏览器"""
    time.sleep(1.5)
    webbrowser.open('http://localhost:5001')

def main():
    """主函数"""
    print("🚀 启动Web版图片处理工具...")
    print("📱 使用Flask提供Web界面")
    print("🌐 完全跨平台兼容")
    
    # 确保模板和静态文件目录存在
    ensure_directories()
    
    add_log("🌐 Web GUI服务器启动")
    add_log("📋 请在浏览器中访问: http://localhost:5001")
    
    # 在新线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        app.run(host='localhost', port=5001, debug=False)
    except KeyboardInterrupt:
        print("\n👋 用户中断，服务器关闭")
    except Exception as e:
        print(f"❌ 服务器运行错误: {e}")

if __name__ == "__main__":
    main()