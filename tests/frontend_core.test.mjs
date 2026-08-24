import assert from "node:assert/strict";
import test from "node:test";

import {
    extractFilenames,
    fileExtension,
    formatBytes,
    safeTextFilename,
    withoutExtension,
} from "../static/js/core.mjs";


test("formats sizes and extensions for public summaries", () => {
    assert.equal(fileExtension("PHOTO.JPEG"), "jpeg");
    assert.equal(formatBytes(1024 * 1024), "1.00 MB");
    assert.equal(withoutExtension("album.v2/photo.final.jpg"), "album.v2/photo.final");
});


test("extracts directory names locally with filters", () => {
    const files = [
        { name: "10.png", size: 10, webkitRelativePath: "photos/sub/10.png" },
        { name: "2.jpg", size: 20, webkitRelativePath: "photos/2.jpg" },
        { name: "封面.webp", size: 30, webkitRelativePath: "photos/封面.webp" },
    ];

    assert.deepEqual(
        extractFilenames(files, {
            source: "directory",
            includeSubdirs: false,
            includePath: true,
            removeExtension: true,
        }),
        ["photos/2", "photos/封面"],
    );
    assert.deepEqual(
        extractFilenames(files, {
            source: "directory",
            includeSubdirs: true,
            includePath: false,
            removeExtension: false,
        }),
        ["2.jpg", "10.png", "封面.webp"],
    );
});


test("sanitizes the local TXT download name", () => {
    assert.equal(safeTextFilename("../daily/list"), "_daily_list.txt");
    assert.equal(safeTextFilename("清单.TXT"), "清单.TXT");
});
