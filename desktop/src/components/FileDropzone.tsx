import React, { useState } from "react";
import { UploadCloud, Folder, FilePlus } from "lucide-react";
import { tauriIpc } from "../services/tauriIpc";
import { FolderFileModal } from "./FolderFileModal";

interface FileDropzoneProps {
  onFilesSelected: (filePaths: string[]) => void;
  multiple?: boolean;
  allowedExtensions?: string[];
}

export const FileDropzone: React.FC<FileDropzoneProps> = ({
  onFilesSelected,
  multiple = false,
  allowedExtensions,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);

  const [folderModalData, setFolderModalData] = useState<{
    folderPath: string;
    files: any[];
  } | null>(null);

  const handleSelectFiles = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const selected = await tauriIpc.pickFiles(multiple, allowedExtensions);
      if (selected.length > 0) {
        onFilesSelected(selected);
      }
    } catch (err) {
      console.error("Error picking files:", err);
    }
  };

  const handleSelectFolder = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const folder = await tauriIpc.pickFolder();
      if (folder) {
        const files = await tauriIpc.listFilesInFolder(folder);
        if (files && files.length > 0) {
          setFolderModalData({ folderPath: folder, files });
        } else {
          alert("Thư mục đã chọn không chứa file tài liệu nào được hỗ trợ (.pdf, .docx, .png, .jpg, .txt, .md, .html).");
        }
      }
    } catch (err) {
      console.error("Error picking folder:", err);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      // In Tauri / webkit, File object often has path
      const paths = droppedFiles
        .map((f) => (f as unknown as { path?: string }).path || f.name)
        .filter(Boolean);
      if (paths.length > 0) {
        onFilesSelected(multiple ? paths : [paths[0]]);
      }
    }
  };

  return (
    <div
      className={`dropzone-container ${isDragOver ? "drag-over" : ""}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleSelectFiles}
    >
      <UploadCloud className="dropzone-icon" />
      <div className="dropzone-title">Thả tài liệu vào đây</div>
      <div className="dropzone-subtitle">
        PDF, DOCX, JPG, PNG và các định dạng được hỗ trợ
      </div>

      <div className="dropzone-actions" onClick={(e) => e.stopPropagation()}>
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleSelectFiles}
        >
          <FilePlus size={16} />
          <span>Chọn file</span>
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleSelectFolder}
        >
          <Folder size={16} />
          <span>Chọn thư mục</span>
        </button>
      </div>

      {folderModalData && (
        <FolderFileModal
          folderPath={folderModalData.folderPath}
          files={folderModalData.files}
          multiple={multiple}
          onSelect={(paths) => {
            onFilesSelected(paths);
            setFolderModalData(null);
          }}
          onClose={() => setFolderModalData(null)}
        />
      )}
    </div>
  );
};
