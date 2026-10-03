pub mod commands;
pub mod python_engine;

use commands::*;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(AppState::new())
        .invoke_handler(tauri::generate_handler![
            execute_ipc,
            cancel_operation,
            get_backend_status,
            open_file,
            open_folder,
            list_files_in_folder
        ])
        .run(tauri::generate_context!())
        .expect("Lỗi khi khởi chạy Document Assistant desktop app");
}
