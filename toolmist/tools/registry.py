"""Product metadata for tools exposed by Toolmist."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDefinition:
    id: str
    name: str
    description: str
    category: str
    execution: str
    limits: tuple
    availability: str = "available"


_TOOLS = (
    ToolDefinition(
        id="image-compress",
        name="图片压缩",
        description="把图片压缩到指定大小并下载为 JPEG。",
        category="image-file",
        execution="server",
        limits=("单张图片", "最大 50 MB", "输出 JPEG"),
    ),
    ToolDefinition(
        id="image-convert",
        name="格式转换",
        description="在 JPG、PNG 和 WebP 之间转换图片。",
        category="image-file",
        execution="server",
        limits=("最多 10 张", "总计 50 MB", "多张打包 ZIP"),
    ),
    ToolDefinition(
        id="filename-extract",
        name="文件名提取",
        description="提取本地文件或目录中的文件名并导出文本。",
        category="image-file",
        execution="browser",
        limits=("不上传文件", "支持目录", "导出 TXT"),
    ),
)


def get_available_tools():
    return tuple(tool for tool in _TOOLS if tool.availability == "available")
