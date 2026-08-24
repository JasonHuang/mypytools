"""Product metadata for tools exposed by Toolmist."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDefinition:
    id: str
    name: str
    description: str
    category: str
    execution: str
    availability: str = "available"


_TOOLS = (
    ToolDefinition(
        id="filename-extract",
        name="文件名提取",
        description="提取本地文件或目录中的文件名并导出文本。",
        category="image-file",
        execution="browser",
    ),
    ToolDefinition(
        id="image-compress",
        name="图片压缩",
        description="把图片压缩到指定大小并下载为 JPEG。",
        category="image-file",
        execution="server",
    ),
    ToolDefinition(
        id="image-convert",
        name="格式转换",
        description="在 JPG、PNG 和 WebP 之间转换图片。",
        category="image-file",
        execution="server",
    ),
)


def get_available_tools():
    return tuple(tool for tool in _TOOLS if tool.availability == "available")
