use crate::python_engine::PythonEngine;
use serde_json::{json, Value};
use std::path::Path;
use std::process::Command;
use std::sync::Mutex;
use tauri::State;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

const CREATE_NO_WINDOW: u32 = 0x08000000;

pub struct AppState {
    pub engine: Mutex<Option<PythonEngine>>,
}

impl AppState {
    pub fn new() -> Self {
        let engine = PythonEngine::new().ok();
        Self {
            engine: Mutex::new(engine),
        }
    }
}

#[tauri::command]
pub async fn execute_ipc(
    request: Value,
    job_id: Option<String>,
    state: State<'_, AppState>,
) -> Result<Value, Value> {
    let engine = {
        let guard = state.engine.lock().map_err(|_| {
            json!({
                "success": false,
                "error": {
                    "code": "STATE_LOCK_ERROR",
                    "message": "Không thể khóa trạng thái ứng dụng."
                }
            })
        })?;

        if let Some(ref eng) = *guard {
            eng.clone()
        } else {
            // Try lazy re-init
            match PythonEngine::new() {
                Ok(eng) => eng,
                Err(err_msg) => {
                    return Err(json!({
                        "success": false,
                        "error": {
                            "code": "BACKEND_UNAVAILABLE",
                            "message": err_msg
                        }
                    }));
                }
            }
        }
    };

    // Execute in blocking thread pool
    tokio::task::spawn_blocking(move || engine.execute_ipc(request, job_id))
        .await
        .map_err(|e| {
            json!({
                "success": false,
                "error": {
                    "code": "ASYNC_TASK_ERROR",
                    "message": format!("Lỗi thực thi tác vụ nền: {}", e)
                }
            })
        })?
}

#[tauri::command]
pub async fn cancel_operation(job_id: String, state: State<'_, AppState>) -> Result<bool, String> {
    let guard = state
        .engine
        .lock()
        .map_err(|e| format!("Lock error: {}", e))?;

    if let Some(ref eng) = *guard {
        Ok(eng.cancel_job(&job_id))
    } else {
        Ok(false)
    }
}

#[tauri::command]
pub async fn get_backend_status(state: State<'_, AppState>) -> Result<Value, String> {
    let mut guard = state
        .engine
        .lock()
        .map_err(|e| format!("Lock error: {}", e))?;

    if guard.is_none() {
        if let Ok(new_eng) = PythonEngine::new() {
            *guard = Some(new_eng);
        }
    }

    if let Some(ref eng) = *guard {
        Ok(eng.get_status())
    } else {
        Ok(json!({
            "ready": false,
            "python_detected": false,
            "python_path": "",
            "python_version": "",
            "backend_path": "",
            "ocr_available": false
        }))
    }
}

#[tauri::command]
pub async fn open_file(path: String) -> Result<(), String> {
    let p = Path::new(&path);
    if !p.exists() {
        return Err(format!("File không tồn tại: {}", path));
    }

    #[cfg(windows)]
    {
        let mut cmd = Command::new("rundll32");
        cmd.args(["url.dll,FileProtocolHandler", &path]);
        cmd.creation_flags(CREATE_NO_WINDOW);
        cmd.spawn().map_err(|e| e.to_string())?;
    }
    #[cfg(not(windows))]
    {
        Command::new("xdg-open")
            .arg(&path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }

    Ok(())
}

#[tauri::command]
pub async fn open_folder(path: String) -> Result<(), String> {
    let p = Path::new(&path);
    if !p.exists() {
        return Err(format!("Đường dẫn không tồn tại: {}", path));
    }

    #[cfg(windows)]
    {
        let mut cmd = Command::new("explorer");
        if p.is_file() {
            cmd.arg(format!("/select,{}", path));
        } else {
            cmd.arg(&path);
        }
        cmd.creation_flags(CREATE_NO_WINDOW);
        cmd.spawn().map_err(|e| e.to_string())?;
    }
    #[cfg(not(windows))]
    {
        let folder = if p.is_file() {
            p.parent().unwrap_or(p)
        } else {
            p
        };
        Command::new("xdg-open")
            .arg(folder)
            .spawn()
            .map_err(|e| e.to_string())?;
    }

    Ok(())
}
