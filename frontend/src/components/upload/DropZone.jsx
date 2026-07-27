import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, FileText } from "lucide-react";

import { useUpload } from "../../../store/upload";

function DropZone() {
  const addFiles = useUpload((state) => state.addFiles);
  const setDragging = useUpload((state) => state.setDragging);

  const onDrop = useCallback(
    (acceptedFiles) => {
      addFiles(acceptedFiles);
      setDragging(false);
    },
    [addFiles, setDragging]
  );

  const {
    getRootProps,
    getInputProps,
    isDragActive,
  } = useDropzone({
    onDrop,
    multiple: true,
    accept: {
      "application/pdf": [".pdf"],
    },
    maxSize: 20 * 1024 * 1024,
    onDragEnter: () => setDragging(true),
    onDragLeave: () => setDragging(false),
  });

  return (
    <div
      {...getRootProps()}
      className={`cursor-pointer rounded-3xl border-2 border-dashed p-10 transition-all duration-300 ${
        isDragActive
          ? "border-primary bg-primary/5"
          : "border-border bg-background hover:border-primary/50"
      }`}
    >
      <input {...getInputProps()} />

      <div className="flex flex-col items-center text-center">

        <div
          className={`mb-6 flex h-20 w-20 items-center justify-center rounded-3xl transition ${
            isDragActive
              ? "bg-primary text-textInverse"
              : "bg-primary/10 text-primary"
          }`}
        >
          <UploadCloud size={40} />
        </div>

        <h2 className="text-xl font-semibold text-text">
          {isDragActive
            ? "Drop your PDFs here"
            : "Upload PDF Documents"}
        </h2>

        <p className="mt-3 max-w-md text-sm leading-7 text-textMuted">
          Drag & drop one or more PDFs here, or click to browse.
          Maximum file size is 20MB.
        </p>

        <div className="mt-8 flex items-center gap-2 rounded-full bg-surface px-4 py-2 text-sm text-textMuted">
          <FileText size={16} />
          PDF files only
        </div>

      </div>
    </div>
  );
}

export default DropZone;