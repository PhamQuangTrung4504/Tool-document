use serde_json::{json, Value};
use std::collections::HashMap;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

const CREATE_NO_WINDOW: u32 = 0x08000000;

#[derive(Clone)]
pub struct PythonEngine {
    pub python_path: PathBuf,
    pub backend_dir: PathBuf,
    active_jobs: Arc<Mutex<HashMap<String, u32>>>,
}

impl PythonEngine {
    pub fn new() -> Result<Self, String> {
        let backend_dir = Self::discover_backend_dir()
            .ok_or_else(|| "Không tìm thấy thư mục backend của Document Assistant.".to_string())?;

        let python_path = Self::discover_python_path(&backend_dir)
            .ok_or_else(|| "Không tìm thấy môi trường Python hợp lệ trên hệ thống.".to_string())?;

        Ok(Self {
            python_path,
            backend_dir,
            active_jobs: Arc::new(Mutex::new(HashMap::new())),
        })
    }

    /// Discovers the backend directory containing app/main.py
    pub fn discover_backend_dir() -> Option<PathBuf> {
        // 1. Env variable
        if let Ok(val) = std::env::var("DOC_ASSISTANT_BACKEND_DIR") {
            let p = PathBuf::from(val);
            if p.join("app").join("main.py").exists() {
                return Some(p);
            }
        }

        // 2. Relative search locations
        let candidates = vec![
            PathBuf::from("backend"),
            PathBuf::from("../backend"),
            PathBuf::from("../../backend"),
            PathBuf::from("."),
        ];

        for cand in candidates {
            if cand.join("app").join("main.py").exists() {
                if let Ok(abs) = cand.canonicalize() {
                    return Some(abs);
                }
                return Some(cand);
            }
        }

        // 3. Search relative to current executable
        if let Ok(exe) = std::env::current_exe() {
            let mut cur = exe.parent();
            for _ in 0..4 {
                if let Some(parent) = cur {
                    let cand = parent.join("backend");
                    if cand.join("app").join("main.py").exists() {
                        return cand.canonicalize().ok().or(Some(cand));
                    }
                    let cand_direct = parent.join("app").join("main.py");
                    if cand_direct.exists() {
                        return Some(parent.to_path_buf());
                    }
                    cur = parent.parent();
                } else {
                    break;
                }
            }
        }

        None
    }

    /// Discovers a valid python executable
    pub fn discover_python_path(backend_dir: &Path) -> Option<PathBuf> {
        // 1. Env variable
        if let Ok(val) = std::env::var("DOC_ASSISTANT_PYTHON") {
            let p = PathBuf::from(&val);
            if p.exists() {
                return Some(p);
            }
        }

        // 2. Virtual environments inside or next to backend
        let venv_candidates = vec![
            backend_dir.join(".venv").join("Scripts").join("python.exe"),
            backend_dir.join("venv").join("Scripts").join("python.exe"),
            backend_dir.join("..").join(".venv").join("Scripts").join("python.exe"),
            PathBuf::from(".venv").join("Scripts").join("python.exe"),
        ];

        for cand in venv_candidates {
            if cand.exists() {
                if let Ok(abs) = cand.canonicalize() {
                    return Some(abs);
                }
                return Some(cand);
            }
        }

        // 3. System python in PATH
        let test_commands = vec!["python", "py"];
        for cmd_name in test_commands {
            let mut cmd = Command::new(cmd_name);
            cmd.arg("--version");
            #[cfg(windows)]
            cmd.creation_flags(CREATE_NO_WINDOW);

            if let Ok(output) = cmd.output() {
                if output.status.success() {
                    // Try to resolve absolute path of python using `where` on Windows
                    let mut where_cmd = Command::new("where");
                    where_cmd.arg(cmd_name);
                    #[cfg(windows)]
                    where_cmd.creation_flags(CREATE_NO_WINDOW);

                    if let Ok(where_out) = where_cmd.output() {
                        if where_out.status.success() {
                            let stdout = String::from_utf8_lossy(&where_out.stdout);
                            if let Some(first_line) = stdout.lines().next() {
                                let trimmed = first_line.trim();
                                if !trimmed.is_empty() {
                                    return Some(PathBuf::from(trimmed));
                                }
                            }
                        }
                    }
                    return Some(PathBuf::from(cmd_name));
                }
            }
        }

        None
    }

    /// Executes an IPC request by piping JSON to `python -m app.main ipc --stdin`
    pub fn execute_ipc(&self, request: Value, job_id: Option<String>) -> Result<Value, Value> {
        let payload_str = match serde_json::to_string(&request) {
            Ok(s) => s,
            Err(e) => {
                return Err(json!({
                    "success": false,
                    "error": {
                        "code": "SERIALIZATION_ERROR",
                        "message": format!("Không thể tuần tự hóa yêu cầu: {}", e)
                    }
                }));
            }
        };

        let mut cmd = Command::new(&self.python_path);
        cmd.current_dir(&self.backend_dir)
            .args(["-m", "app.main", "ipc", "--stdin"])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        #[cfg(windows)]
        cmd.creation_flags(CREATE_NO_WINDOW);

        let mut child = match cmd.spawn() {
            Ok(c) => c,
            Err(e) => {
                return Err(json!({
                    "success": false,
                    "error": {
                        "code": "SPAWN_ERROR",
                        "message": format!("Không thể khởi chạy tiến trình Python backend: {}", e)
                    }
                }));
            }
        };

        let pid = child.id();
        if let Some(ref jid) = job_id {
            if let Ok(mut jobs) = self.active_jobs.lock() {
                jobs.insert(jid.clone(), pid);
            }
        }

        // Pipe JSON payload into stdin
        if let Some(mut stdin) = child.stdin.take() {
            if let Err(e) = stdin.write_all(payload_str.as_bytes()) {
                if let Some(ref jid) = job_id {
                    if let Ok(mut jobs) = self.active_jobs.lock() {
                        jobs.remove(jid);
                    }
                }
                return Err(json!({
                    "success": false,
                    "error": {
                        "code": "IPC_PIPE_ERROR",
                        "message": format!("Không thể gửi dữ liệu đến backend qua stdin: {}", e)
                    }
                }));
            }
            // stdin is dropped here, sending EOF
        }

        let output = match child.wait_with_output() {
            Ok(o) => o,
            Err(e) => {
                if let Some(ref jid) = job_id {
                    if let Ok(mut jobs) = self.active_jobs.lock() {
                        jobs.remove(jid);
                    }
                }
                return Err(json!({
                    "success": false,
                    "error": {
                        "code": "PROCESS_WAIT_ERROR",
                        "message": format!("Lỗi khi đợi tiến trình backend: {}", e)
                    }
                }));
            }
        };

        // Clean up job tracker
        if let Some(ref jid) = job_id {
            if let Ok(mut jobs) = self.active_jobs.lock() {
                jobs.remove(jid);
            }
        }

        let stdout_str = String::from_utf8_lossy(&output.stdout);
        let trimmed_stdout = stdout_str.trim().trim_start_matches('\u{feff}');
        let json_target = match (trimmed_stdout.find('{'), trimmed_stdout.rfind('}')) {
            (Some(start), Some(end)) if start <= end => &trimmed_stdout[start..=end],
            _ => trimmed_stdout,
        };

        if let Ok(json_res) = serde_json::from_str::<Value>(json_target) {
            let is_success = json_res.get("success").and_then(|v| v.as_bool()).unwrap_or(false);
            if is_success {
                Ok(json_res)
            } else {
                Err(json_res)
            }
        } else {
            let stderr_str = String::from_utf8_lossy(&output.stderr);
            Err(json!({
                "success": false,
                "error": {
                    "code": "INVALID_BACKEND_OUTPUT",
                    "message": if !stderr_str.trim().is_empty() {
                        format!("Tiến trình backend trả về lỗi: {}", stderr_str.trim())
                    } else if !trimmed_stdout.is_empty() {
                        format!("Phản hồi backend không đúng định dạng JSON: {}", trimmed_stdout)
                    } else {
                        "Backend không trả về dữ liệu.".to_string()
                    }
                }
            }))
        }
    }

    /// Cancels a running job by killing its process
    pub fn cancel_job(&self, job_id: &str) -> bool {
        let pid_opt = {
            if let Ok(mut jobs) = self.active_jobs.lock() {
                jobs.remove(job_id)
            } else {
                None
            }
        };

        if let Some(pid) = pid_opt {
            #[cfg(windows)]
            {
                let _ = Command::new("taskkill")
                    .args(["/F", "/T", "/PID", &pid.to_string()])
                    .creation_flags(CREATE_NO_WINDOW)
                    .output();
            }
            #[cfg(not(windows))]
            {
                let _ = Command::new("kill").args(["-9", &pid.to_string()]).output();
            }
            return true;
        }

        false
    }

    /// Gets health and environment status of the backend
    pub fn get_status(&self) -> Value {
        let mut py_version = String::new();
        let mut cmd_ver = Command::new(&self.python_path);
        cmd_ver.arg("--version");
        #[cfg(windows)]
        cmd_ver.creation_flags(CREATE_NO_WINDOW);

        if let Ok(out) = cmd_ver.output() {
            py_version = String::from_utf8_lossy(&out.stdout)
                .trim()
                .to_string();
            if py_version.is_empty() {
                py_version = String::from_utf8_lossy(&out.stderr).trim().to_string();
            }
        }

        let main_py = self.backend_dir.join("app").join("main.py");
        let backend_ready = main_py.exists();

        // Check if paddle / OCR dependencies are available
        let mut ocr_ready = false;
        let mut cmd_ocr = Command::new(&self.python_path);
        cmd_ocr
            .current_dir(&self.backend_dir)
            .args(["-c", "import paddle; print('OK')"]);
        #[cfg(windows)]
        cmd_ocr.creation_flags(CREATE_NO_WINDOW);

        if let Ok(out) = cmd_ocr.output() {
            if String::from_utf8_lossy(&out.stdout).contains("OK") {
                ocr_ready = true;
            }
        }

        json!({
            "ready": backend_ready && !py_version.is_empty(),
            "python_detected": !py_version.is_empty(),
            "python_path": self.python_path.to_string_lossy(),
            "python_version": py_version,
            "backend_path": self.backend_dir.to_string_lossy(),
            "ocr_available": ocr_ready
        })
    }
}
