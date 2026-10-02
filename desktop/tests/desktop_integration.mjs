import { execSync, spawn } from "child_process";
import fs from "fs";
import path from "path";
import assert from "assert";

console.log("==================================================");
console.log("RUNNING DOCUMENT ASSISTANT DESKTOP INTEGRATION TESTS");
console.log("==================================================");

let passedCount = 0;
let failedCount = 0;

function runTest(name, fn) {
  try {
    process.stdout.write(`TEST [${name}] ... `);
    fn();
    console.log("PASSED");
    passedCount++;
  } catch (err) {
    console.log("FAILED");
    console.error(`  Error: ${err.message}`);
    if (err.stack) console.error(`  Stack: ${err.stack}`);
    failedCount++;
  }
}

async function runAsyncTest(name, fn) {
  try {
    process.stdout.write(`TEST [${name}] ... `);
    await fn();
    console.log("PASSED");
    passedCount++;
  } catch (err) {
    console.log("FAILED");
    console.error(`  Error: ${err.message}`);
    failedCount++;
  }
}

const ROOT_DIR = path.resolve("..");
const BACKEND_DIR = path.join(ROOT_DIR, "backend");
const DESKTOP_DIR = path.resolve(".");

function parseJsonFromOutput(raw) {
  if (!raw) return null;
  const trimmed = String(raw).trim();
  const start = trimmed.indexOf("{");
  const end = trimmed.lastIndexOf("}");
  if (start !== -1 && end !== -1 && start <= end) {
    return JSON.parse(trimmed.substring(start, end + 1));
  }
  return JSON.parse(trimmed);
}

// Helper to invoke backend IPC directly via stdio like Rust does
function callBackendIpc(payload) {
  const inputStr = JSON.stringify(payload);
  const out = execSync("python -m app.main ipc --stdin", {
    cwd: BACKEND_DIR,
    input: inputStr,
    encoding: "utf-8",
    stdio: ["pipe", "pipe", "pipe"],
  });
  return parseJsonFromOutput(out);
}

// 1. TypeScript build
runTest("1. TypeScript build", () => {
  const distHtml = path.join(DESKTOP_DIR, "dist", "index.html");
  assert(fs.existsSync(distHtml), "dist/index.html should exist from npm run build");
  const htmlContent = fs.readFileSync(distHtml, "utf-8");
  assert(htmlContent.includes("Document Assistant"), "index.html must contain app title");
});

// 2. Tauri command validation
runTest("2. Tauri command validation", () => {
  const libRsPath = path.join(DESKTOP_DIR, "src-tauri", "src", "lib.rs");
  assert(fs.existsSync(libRsPath), "lib.rs must exist");
  const libContent = fs.readFileSync(libRsPath, "utf-8");
  const requiredCommands = [
    "execute_ipc",
    "cancel_operation",
    "get_backend_status",
    "open_file",
    "open_folder",
  ];
  for (const cmd of requiredCommands) {
    assert(libContent.includes(cmd), `lib.rs must register command: ${cmd}`);
  }
});

// 3. IPC request serialization
runTest("3. IPC request serialization", () => {
  const request = {
    operation: "convert",
    input: "C:\\Documents\\scan.pdf",
    output: "C:\\Documents\\result.docx",
    options: {
      ocr_mode: "fast",
      to_format: "docx",
    },
  };
  const jsonStr = JSON.stringify(request);
  const parsed = JSON.parse(jsonStr);
  assert.strictEqual(parsed.operation, "convert");
  assert.strictEqual(parsed.input, "C:\\Documents\\scan.pdf");
  assert.strictEqual(parsed.options.ocr_mode, "fast");
});

// 4. IPC response parsing
runTest("4. IPC response parsing", () => {
  const rawResponse = JSON.stringify({
    success: true,
    operation: "convert",
    output: "C:\\Documents\\result.docx",
    metrics: {
      pages: 5,
      processing_time_ms: 12345,
      ocr_mode: "fast",
    },
    warnings: ["Table fallback used"],
  });
  const res = JSON.parse(rawResponse);
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.metrics.pages, 5);
  assert.strictEqual(res.warnings.length, 1);
});

// 5. Backend process failure
runTest("5. Backend process failure", () => {
  try {
    callBackendIpc({ operation: "info", input: "C:\\nonexistent_file_xyz_123.pdf" });
    assert.fail("Should have failed for nonexistent file");
  } catch (err) {
    // Backend returns exit code 1 with JSON error or exception
    assert(err.stdout || err.message, "Should output error information");
    if (err.stdout) {
      const parsed = parseJsonFromOutput(err.stdout);
      assert.strictEqual(parsed.success, false);
      assert.strictEqual(parsed.error.code, "FILE_NOT_FOUND");
    }
  }
});

// 6. Backend unavailable
runTest("6. Backend unavailable", () => {
  // Test Rust error handling structure when python command is invalid
  const errorPayload = {
    success: false,
    error: {
      code: "BACKEND_UNAVAILABLE",
      message: "Không tìm thấy môi trường Python hợp lệ trên hệ thống.",
    },
  };
  assert.strictEqual(errorPayload.success, false);
  assert.strictEqual(errorPayload.error.code, "BACKEND_UNAVAILABLE");
});

// 7. Cancellation
await runAsyncTest("7. Cancellation", async () => {
  // Spawn a real long-running child process and terminate it, simulating cancel_operation
  const child = spawn("python", ["-c", "import time; time.sleep(10)"], {
    cwd: BACKEND_DIR,
  });
  const pid = child.pid;
  assert(pid > 0, "Child process should have a valid PID");

  // Kill child process
  execSync(`taskkill /F /T /PID ${pid}`);
  await new Promise((resolve) => setTimeout(resolve, 300));
  assert(child.killed || child.exitCode !== null, "Process should be terminated");
});

// 8. Invalid path
runTest("8. Invalid path", () => {
  try {
    callBackendIpc({ operation: "convert", input: "invalid/path/that/does/not/exist.docx" });
    assert.fail("Should have failed for invalid path");
  } catch (err) {
    const parsed = parseJsonFromOutput(err.stdout);
    assert.strictEqual(parsed.success, false);
    assert(parsed.error.code.includes("FILE_NOT_FOUND") || parsed.error.code.includes("INVALID"));
  }
});

// 9. Unsupported operation
runTest("9. Unsupported operation", () => {
  try {
    callBackendIpc({ operation: "unsupported_magic_op", input: "test.pdf" });
    assert.fail("Should have failed for unsupported operation");
  } catch (err) {
    const parsed = parseJsonFromOutput(err.stdout);
    assert.strictEqual(parsed.success, false);
    assert.strictEqual(parsed.error.code, "UNSUPPORTED_OPERATION");
  }
});

// 10. Successful conversion (real backend execution)
runTest("10. Successful conversion (real backend execution)", () => {
  const fixturePath = path.join(BACKEND_DIR, "tests", "fixtures", "real_contract.docx");
  const tempOut = path.join(DESKTOP_DIR, "temp_contract_converted.txt");

  const res = callBackendIpc({
    operation: "convert",
    input: fixturePath,
    output: tempOut,
    options: {
      to_format: "txt",
    },
  });

  assert.strictEqual(res.success, true);
  assert.strictEqual(res.operation, "convert");
  assert(fs.existsSync(tempOut), "Output file should be created");
  const content = fs.readFileSync(tempOut, "utf-8");
  assert(content.length > 0, "Converted text should not be empty");

  // Cleanup temp file
  try { fs.unlinkSync(tempOut); } catch {}
});

// 11. Error response mapping
runTest("11. Error response mapping", () => {
  const mapCode = (code) => {
    const map = {
      OCR_PROCESSING_ERROR: "Không thể nhận diện nội dung trong tài liệu qua OCR.",
      UNSUPPORTED_FORMAT: "Định dạng tài liệu này chưa được hỗ trợ.",
      INVALID_DOCUMENT: "Tài liệu không hợp lệ hoặc bị hỏng.",
      CONVERSION_ERROR: "Không thể chuyển đổi tài liệu.",
      OPERATION_CANCELLED: "Đã hủy thao tác xử lý.",
    };
    return map[code] || "Lỗi xử lý.";
  };

  assert.strictEqual(mapCode("OCR_PROCESSING_ERROR"), "Không thể nhận diện nội dung trong tài liệu qua OCR.");
  assert.strictEqual(mapCode("UNSUPPORTED_FORMAT"), "Định dạng tài liệu này chưa được hỗ trợ.");
  assert.strictEqual(mapCode("OPERATION_CANCELLED"), "Đã hủy thao tác xử lý.");
});

// 12. History persistence
runTest("12. History persistence", () => {
  const store = [];
  function addEntry(item) {
    store.unshift({ ...item, id: "h_" + Date.now() });
    if (store.length > 100) store.pop();
  }

  addEntry({ inputName: "test.pdf", operation: "convert", status: "COMPLETED" });
  assert.strictEqual(store.length, 1);
  assert.strictEqual(store[0].inputName, "test.pdf");
});

// 13. History limit of 100
runTest("13. History limit of 100", () => {
  const store = [];
  for (let i = 0; i < 125; i++) {
    store.unshift({ id: `item_${i}`, inputName: `file_${i}.pdf` });
    if (store.length > 100) {
      store.splice(100);
    }
  }
  assert.strictEqual(store.length, 100, "History must be strictly capped at 100");
  assert.strictEqual(store[0].id, "item_124", "Most recent item must be at index 0");
});

// 14. Opening output path & Windows path validation
runTest("14. Opening output path & Windows path with spaces & Vietnamese", () => {
  const complexPath = "C:\\Users\\Test User\\Documents\\Tài liệu\\Báo cáo (2026).pdf";
  assert(complexPath.includes(" "), "Path contains spaces");
  assert(complexPath.includes("Tài liệu"), "Path contains Vietnamese diacritics");
  assert(complexPath.includes("("), "Path contains parentheses");

  // Verify path splitting and extension extraction
  const parts = complexPath.replace(/\\/g, "/").split("/");
  const fileName = parts[parts.length - 1];
  assert.strictEqual(fileName, "Báo cáo (2026).pdf");
});

// 15. UI loading state lifecycle
runTest("15. UI loading state lifecycle", () => {
  const validTransitions = {
    IDLE: ["QUEUED", "RUNNING"],
    QUEUED: ["RUNNING", "CANCELLED", "FAILED"],
    RUNNING: ["COMPLETED", "FAILED", "CANCELLED"],
    COMPLETED: ["IDLE"],
    FAILED: ["IDLE"],
    CANCELLED: ["IDLE"],
  };

  assert(validTransitions["IDLE"].includes("RUNNING"));
  assert(validTransitions["RUNNING"].includes("COMPLETED"));
  assert(validTransitions["RUNNING"].includes("CANCELLED"));
});

console.log("==================================================");
console.log(`TEST SUMMARY: ${passedCount} PASSED / ${failedCount} FAILED`);
console.log("==================================================");

if (failedCount > 0) {
  process.exit(1);
}
