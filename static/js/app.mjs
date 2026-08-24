// Toolmist public tool workflows. Dynamic content is written through DOM APIs.
import {
    extractFilenames,
    fileExtension,
    formatBytes,
    safeTextFilename,
    totalSize,
} from "./core.mjs";

document.addEventListener("DOMContentLoaded", () => {
    const workspace = document.querySelector("#workspace");
    const maxUploadBytes = Number(workspace.dataset.maxUploadMb) * 1024 * 1024;
    const maxFiles = Number(workspace.dataset.maxFiles);
    const serverObjectUrls = new Set();

    const state = {
        compressFiles: [],
        convertFiles: [],
        filenameFiles: [],
        filenameSource: "files",
        filenameObjectUrl: null,
    };

    const compressionExtensions = new Set([
        "jpg", "jpeg", "png", "webp", "heic", "heif",
    ]);
    const conversionExtensions = new Set([
        "jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff", "heic", "heif",
    ]);

    function clearElement(element) {
        element.replaceChildren();
        element.hidden = true;
    }

    function showStatus(element, message, type = "info") {
        element.textContent = message;
        element.classList.toggle("is-error", type === "error");
        element.classList.toggle("is-busy", type === "busy");
        element.hidden = false;
    }

    function clearFeedback(status, result) {
        clearElement(status);
        clearElement(result);
    }

    function renderFileSummary(element, files, leadText) {
        if (!files.length) {
            clearElement(element);
            return;
        }
        const strong = document.createElement("strong");
        strong.textContent = leadText;
        const detail = document.createElement("span");
        detail.textContent = ` · ${formatBytes(totalSize(files))}`;
        element.replaceChildren(strong, detail);
        element.title = files.length === 1 ? files[0].name : files.map((file) => file.name).join("\n");
        element.hidden = false;
    }

    function buttonLabel(button, label, showArrow) {
        const labelNode = document.createTextNode(label);
        if (!showArrow) {
            button.replaceChildren(labelNode);
            return;
        }
        const arrow = document.createElement("span");
        arrow.setAttribute("aria-hidden", "true");
        arrow.textContent = "→";
        button.replaceChildren(labelNode, arrow);
    }

    function setBusy(form, busy, busyLabel) {
        const submit = form.querySelector("button[type='submit']");
        if (!submit.dataset.idleLabel) {
            submit.dataset.idleLabel = submit.textContent.replace("→", "").trim();
        }
        form.setAttribute("aria-busy", String(busy));
        form.querySelectorAll("button, input, select").forEach((control) => {
            control.disabled = busy;
        });
        buttonLabel(
            submit,
            busy ? busyLabel : submit.dataset.idleLabel,
            !busy,
        );
    }

    function validateServerFiles(files, options) {
        if (!files.length) return options.emptyMessage;
        if (files.length > options.maxCount) {
            return `每次最多选择 ${options.maxCount} 张图片`;
        }
        const unsupported = files.find(
            (file) => !options.extensions.has(fileExtension(file.name)),
        );
        if (unsupported) return `不支持这种文件格式：${unsupported.name}`;
        if (totalSize(files) > maxUploadBytes) {
            return `文件总大小不能超过 ${workspace.dataset.maxUploadMb} MB`;
        }
        return null;
    }

    async function submitJob(endpoint, formData) {
        let response;
        try {
            response = await fetch(endpoint, { method: "POST", body: formData });
        } catch (_error) {
            throw new Error("无法连接处理服务，请检查网络后重试");
        }

        let payload = null;
        try {
            payload = await response.json();
        } catch (_error) {
            throw new Error("处理服务返回了无法识别的响应");
        }
        if (!response.ok || !payload.ok) {
            throw new Error(payload?.error?.message || "处理失败，请稍后重试");
        }
        return payload;
    }

    function createMetaList(rows) {
        const list = document.createElement("dl");
        list.className = "result-card__meta";
        rows.forEach(([label, value]) => {
            const item = document.createElement("div");
            const term = document.createElement("dt");
            const detail = document.createElement("dd");
            term.textContent = label;
            detail.textContent = value;
            item.append(term, detail);
            list.append(item);
        });
        return list;
    }

    function triggerBrowserDownload(blob, filename) {
        const objectUrl = URL.createObjectURL(blob);
        serverObjectUrls.add(objectUrl);
        const anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = filename;
        anchor.hidden = true;
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
        window.setTimeout(() => {
            URL.revokeObjectURL(objectUrl);
            serverObjectUrls.delete(objectUrl);
        }, 1000);
    }

    function attachServerDownload(anchor, artifact, status) {
        anchor.addEventListener("click", async (event) => {
            event.preventDefault();
            anchor.setAttribute("aria-disabled", "true");
            showStatus(status, "正在准备下载…", "busy");
            try {
                const response = await fetch(artifact.download_url);
                if (!response.ok) {
                    let message = "结果已不可下载，请重新处理文件";
                    try {
                        const payload = await response.json();
                        message = payload?.error?.message || message;
                    } catch (_error) {
                        // Keep the safe fallback message.
                    }
                    throw new Error(message);
                }
                triggerBrowserDownload(await response.blob(), artifact.name);
                showStatus(status, "下载已开始。结果在过期前可以再次下载。", "info");
            } catch (error) {
                showStatus(status, error.message, "error");
            } finally {
                anchor.removeAttribute("aria-disabled");
            }
        });
    }

    function showResult(container, options) {
        const top = document.createElement("div");
        top.className = "result-card__top";
        const copy = document.createElement("div");
        const label = document.createElement("p");
        label.className = "result-card__label";
        label.textContent = "处理完成";
        const title = document.createElement("h3");
        title.textContent = options.title;
        copy.append(label, title);

        const download = document.createElement("a");
        download.className = "download-button";
        download.href = options.url;
        download.download = options.filename;
        download.textContent = "下载结果 ↓";
        if (options.serverArtifact) {
            attachServerDownload(download, options.serverArtifact, options.status);
        }
        top.append(copy, download);

        const note = document.createElement("p");
        note.className = "result-card__note";
        note.textContent = options.note;
        container.replaceChildren(top, createMetaList(options.rows), note);
        container.hidden = false;
        container.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function setupTabs() {
        const tabs = Array.from(document.querySelectorAll("[data-tool-target]"));
        const panels = Array.from(document.querySelectorAll("[role='tabpanel']"));

        function activateTool(toolId, focusTab = false) {
            tabs.forEach((tab) => {
                const active = tab.dataset.toolTarget === toolId;
                tab.classList.toggle("is-active", active);
                tab.setAttribute("aria-selected", String(active));
                tab.tabIndex = active ? 0 : -1;
                if (active && focusTab) tab.focus();
            });
            panels.forEach((panel) => {
                panel.hidden = panel.id !== `panel-${toolId}`;
            });
            window.history.replaceState(null, "", `#${toolId}`);
        }

        tabs.forEach((tab, index) => {
            tab.addEventListener("click", () => activateTool(tab.dataset.toolTarget));
            tab.addEventListener("keydown", (event) => {
                const keys = ["ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "Home", "End"];
                if (!keys.includes(event.key)) return;
                event.preventDefault();
                let nextIndex = index;
                if (["ArrowDown", "ArrowRight"].includes(event.key)) nextIndex = (index + 1) % tabs.length;
                if (["ArrowUp", "ArrowLeft"].includes(event.key)) nextIndex = (index - 1 + tabs.length) % tabs.length;
                if (event.key === "Home") nextIndex = 0;
                if (event.key === "End") nextIndex = tabs.length - 1;
                activateTool(tabs[nextIndex].dataset.toolTarget, true);
            });
        });

        const requestedTool = window.location.hash.slice(1);
        if (tabs.some((tab) => tab.dataset.toolTarget === requestedTool)) {
            activateTool(requestedTool);
        }
    }

    function setupRange(inputSelector, outputSelector, formatter) {
        const input = document.querySelector(inputSelector);
        const output = document.querySelector(outputSelector);
        const update = () => { output.value = formatter(input.value); };
        input.addEventListener("input", update);
        input.form?.addEventListener("reset", () => window.setTimeout(update));
    }

    function setupDropzone(input, dropzone, onFiles) {
        input.addEventListener("change", () => onFiles(Array.from(input.files)));
        ["dragenter", "dragover"].forEach((name) => {
            dropzone.addEventListener(name, (event) => {
                event.preventDefault();
                dropzone.classList.add("is-dragging");
            });
        });
        ["dragleave", "dragend"].forEach((name) => {
            dropzone.addEventListener(name, () => dropzone.classList.remove("is-dragging"));
        });
        dropzone.addEventListener("drop", (event) => {
            event.preventDefault();
            dropzone.classList.remove("is-dragging");
            const files = Array.from(event.dataTransfer?.files || []);
            onFiles(input.multiple ? files : files.slice(0, 1));
        });
    }

    function setupCompression() {
        const form = document.querySelector("#compress-form");
        const input = document.querySelector("#compress-file");
        const summary = document.querySelector("#compress-file-summary");
        const status = document.querySelector("#compress-status");
        const result = document.querySelector("#compress-result");

        const selectFiles = (files) => {
            state.compressFiles = files.slice(0, 1);
            clearFeedback(status, result);
            renderFileSummary(
                summary,
                state.compressFiles,
                state.compressFiles[0]?.name || "",
            );
            const error = validateServerFiles(state.compressFiles, {
                emptyMessage: "请选择一张需要压缩的图片",
                maxCount: 1,
                extensions: compressionExtensions,
            });
            if (error) showStatus(status, error, "error");
        };

        setupDropzone(input, document.querySelector("#compress-dropzone"), selectFiles);
        document.querySelector("#target-size").addEventListener("input", () => {
            clearFeedback(status, result);
        });
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            clearFeedback(status, result);
            const error = validateServerFiles(state.compressFiles, {
                emptyMessage: "请选择一张需要压缩的图片",
                maxCount: 1,
                extensions: compressionExtensions,
            });
            if (error) {
                showStatus(status, error, "error");
                return;
            }

            const formData = new FormData();
            formData.append("file", state.compressFiles[0]);
            formData.append("target_size_mb", document.querySelector("#target-size").value);
            setBusy(form, true, "正在压缩…");
            showStatus(status, "正在安全上传并压缩图片，请保持页面打开…", "busy");
            try {
                const payload = await submitJob(
                    "/api/v1/tools/image-compress/jobs",
                    formData,
                );
                const artifact = payload.artifacts[0];
                const reduction = payload.summary.input_size > 0
                    ? (1 - payload.summary.output_size / payload.summary.input_size) * 100
                    : 0;
                const ratioText = reduction >= 0
                    ? `减少 ${reduction.toFixed(1)}%`
                    : `增加 ${Math.abs(reduction).toFixed(1)}%`;
                showStatus(status, "压缩完成，结果已准备好。", "info");
                showResult(result, {
                    title: artifact.name,
                    filename: artifact.name,
                    url: artifact.download_url,
                    serverArtifact: artifact,
                    status,
                    rows: [
                        ["原始大小", formatBytes(payload.summary.input_size)],
                        ["结果大小", formatBytes(payload.summary.output_size)],
                        ["体积变化", ratioText],
                    ],
                    note: `临时结果将在 ${new Date(payload.job.expires_at).toLocaleString()} 前可下载。`,
                });
            } catch (submitError) {
                showStatus(status, submitError.message, "error");
            } finally {
                setBusy(form, false, "");
            }
        });

        form.addEventListener("reset", () => {
            state.compressFiles = [];
            input.value = "";
            clearElement(summary);
            clearFeedback(status, result);
        });
    }

    function setupConversion() {
        const form = document.querySelector("#convert-form");
        const input = document.querySelector("#convert-files");
        const summary = document.querySelector("#convert-file-summary");
        const status = document.querySelector("#convert-status");
        const result = document.querySelector("#convert-result");

        const selectFiles = (files) => {
            state.convertFiles = files;
            clearFeedback(status, result);
            renderFileSummary(
                summary,
                files,
                files.length === 1 ? files[0].name : `已选择 ${files.length} 张图片`,
            );
            const error = validateServerFiles(files, {
                emptyMessage: "请选择需要转换的图片",
                maxCount: maxFiles,
                extensions: conversionExtensions,
            });
            if (error) showStatus(status, error, "error");
        };

        setupDropzone(input, document.querySelector("#convert-dropzone"), selectFiles);
        ["#target-format", "#convert-quality"].forEach((selector) => {
            document.querySelector(selector).addEventListener("input", () => {
                clearFeedback(status, result);
            });
        });
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            clearFeedback(status, result);
            const error = validateServerFiles(state.convertFiles, {
                emptyMessage: "请选择需要转换的图片",
                maxCount: maxFiles,
                extensions: conversionExtensions,
            });
            if (error) {
                showStatus(status, error, "error");
                return;
            }

            const formData = new FormData();
            state.convertFiles.forEach((file) => formData.append("files", file));
            formData.append("output_format", document.querySelector("#target-format").value);
            formData.append("quality", document.querySelector("#convert-quality").value);
            setBusy(form, true, "正在转换…");
            showStatus(status, `正在上传并转换 ${state.convertFiles.length} 张图片…`, "busy");
            try {
                const payload = await submitJob(
                    "/api/v1/tools/image-convert/jobs",
                    formData,
                );
                const artifact = payload.artifacts[0];
                showStatus(status, "格式转换完成，结果已准备好。", "info");
                showResult(result, {
                    title: artifact.name,
                    filename: artifact.name,
                    url: artifact.download_url,
                    serverArtifact: artifact,
                    status,
                    rows: [
                        ["输入文件", `${payload.summary.input_count} 张`],
                        ["输入总大小", formatBytes(payload.summary.input_size)],
                        ["结果大小", formatBytes(payload.summary.output_size)],
                        ["目标格式", payload.summary.output_format.toUpperCase()],
                    ],
                    note: `临时结果将在 ${new Date(payload.job.expires_at).toLocaleString()} 前可下载。`,
                });
            } catch (submitError) {
                showStatus(status, submitError.message, "error");
            } finally {
                setBusy(form, false, "");
            }
        });

        form.addEventListener("reset", () => {
            state.convertFiles = [];
            input.value = "";
            clearElement(summary);
            clearFeedback(status, result);
        });
    }

    function setupFilenameExtraction() {
        const form = document.querySelector("#filename-form");
        const fileInput = document.querySelector("#filename-files");
        const directoryInput = document.querySelector("#filename-directory");
        const summary = document.querySelector("#filename-file-summary");
        const status = document.querySelector("#filename-status");
        const result = document.querySelector("#filename-result");

        const selectLocalFiles = (files, source) => {
            if (state.filenameObjectUrl) {
                URL.revokeObjectURL(state.filenameObjectUrl);
                state.filenameObjectUrl = null;
            }
            state.filenameFiles = files;
            state.filenameSource = source;
            if (source === "files") directoryInput.value = "";
            if (source === "directory") fileInput.value = "";
            clearFeedback(status, result);
            renderFileSummary(
                summary,
                files,
                files.length ? `已在本地读取 ${files.length} 个文件` : "",
            );
        };
        fileInput.addEventListener("change", () => {
            selectLocalFiles(Array.from(fileInput.files), "files");
        });
        directoryInput.addEventListener("change", () => {
            selectLocalFiles(Array.from(directoryInput.files), "directory");
        });

        form.addEventListener("submit", (event) => {
            event.preventDefault();
            clearFeedback(status, result);
            if (!state.filenameFiles.length) {
                showStatus(status, "请先选择文件或目录", "error");
                return;
            }

            const includeSubdirs = document.querySelector("#include-subdirs").checked;
            const includePath = document.querySelector("#include-relative-path").checked;
            const removeExtension = document.querySelector("#remove-extension").checked;
            const names = extractFilenames(state.filenameFiles, {
                source: state.filenameSource,
                includeSubdirs,
                includePath,
                removeExtension,
            });

            if (!names.length) {
                showStatus(status, "当前选项下没有可导出的文件名", "error");
                return;
            }
            if (state.filenameObjectUrl) URL.revokeObjectURL(state.filenameObjectUrl);
            const blob = new Blob(["\ufeff", names.join("\n"), "\n"], {
                type: "text/plain;charset=utf-8",
            });
            state.filenameObjectUrl = URL.createObjectURL(blob);
            const filename = safeTextFilename(document.querySelector("#filename-output").value);
            showStatus(status, "TXT 已在浏览器本地生成，没有发送网络请求。", "info");
            showResult(result, {
                title: filename,
                filename,
                url: state.filenameObjectUrl,
                rows: [
                    ["文件名数量", `${names.length} 个`],
                    ["TXT 大小", formatBytes(blob.size)],
                    ["处理位置", "当前浏览器"],
                ],
                note: "这个下载由浏览器即时生成，刷新或关闭页面后不会保留。",
            });
        });

        form.addEventListener("reset", () => {
            state.filenameFiles = [];
            state.filenameSource = "files";
            fileInput.value = "";
            directoryInput.value = "";
            if (state.filenameObjectUrl) {
                URL.revokeObjectURL(state.filenameObjectUrl);
                state.filenameObjectUrl = null;
            }
            clearElement(summary);
            clearFeedback(status, result);
        });
    }

    setupTabs();
    setupRange("#target-size", "#target-size-output", (value) => `${Number(value).toFixed(1)} MB`);
    setupRange("#convert-quality", "#convert-quality-output", (value) => value);
    setupCompression();
    setupConversion();
    setupFilenameExtraction();

    window.addEventListener("beforeunload", () => {
        if (state.filenameObjectUrl) URL.revokeObjectURL(state.filenameObjectUrl);
        serverObjectUrls.forEach((url) => URL.revokeObjectURL(url));
    });
});
