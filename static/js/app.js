"use strict";

document.addEventListener("DOMContentLoaded", () => {
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
            const navigationKeys = [
                "ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "Home", "End",
            ];
            if (!navigationKeys.includes(event.key)) return;
            event.preventDefault();
            let nextIndex = index;
            if (["ArrowDown", "ArrowRight"].includes(event.key)) {
                nextIndex = (index + 1) % tabs.length;
            }
            if (["ArrowUp", "ArrowLeft"].includes(event.key)) {
                nextIndex = (index - 1 + tabs.length) % tabs.length;
            }
            if (event.key === "Home") nextIndex = 0;
            if (event.key === "End") nextIndex = tabs.length - 1;
            activateTool(tabs[nextIndex].dataset.toolTarget, true);
        });
    });

    const requestedTool = window.location.hash.slice(1);
    if (tabs.some((tab) => tab.dataset.toolTarget === requestedTool)) {
        activateTool(requestedTool);
    }

    const targetSize = document.querySelector("#target-size");
    const targetOutput = document.querySelector("#target-size-output");
    targetSize.addEventListener("input", () => {
        targetOutput.value = `${Number(targetSize.value).toFixed(1)} MB`;
    });

    const quality = document.querySelector("#convert-quality");
    const qualityOutput = document.querySelector("#convert-quality-output");
    quality.addEventListener("input", () => {
        qualityOutput.value = quality.value;
    });
});
