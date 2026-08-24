// Pure browser helpers kept independent for direct unit testing.
export function fileExtension(name) {
    const dot = name.lastIndexOf(".");
    return dot > -1 ? name.slice(dot + 1).toLowerCase() : "";
}

export function formatBytes(bytes) {
    if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), 3);
    const value = bytes / (1024 ** index);
    return `${value.toFixed(index === 0 ? 0 : 2)} ${units[index]}`;
}

export function totalSize(files) {
    return files.reduce((sum, file) => sum + file.size, 0);
}

export function withoutExtension(path) {
    const slash = path.lastIndexOf("/");
    const dot = path.lastIndexOf(".");
    return dot > slash ? path.slice(0, dot) : path;
}

export function safeTextFilename(value) {
    const cleaned = (value || "filenames.txt")
        .replace(/[\\/:*?"<>|\u0000-\u001f\u007f]/g, "_")
        .replace(/^\.+|\.+$/g, "")
        .trim()
        .slice(0, 80) || "filenames.txt";
    return cleaned.toLowerCase().endsWith(".txt") ? cleaned : `${cleaned}.txt`;
}

export function extractFilenames(files, options) {
    return files
        .filter((file) => {
            if (options.source !== "directory" || options.includeSubdirs) return true;
            const relative = file.webkitRelativePath || file.name;
            return relative.split("/").length <= 2;
        })
        .map((file) => {
            const relative = file.webkitRelativePath || file.name;
            const value = options.includePath ? relative : file.name;
            return options.removeExtension ? withoutExtension(value) : value;
        })
        .filter(Boolean)
        .sort((left, right) => left.localeCompare(right, "zh-CN", { numeric: true }));
}
