import {
  FileText,
  Trash2,
  CheckCircle2,
  LoaderCircle,
  Upload,
} from "lucide-react";

import ProgressBar from "./ProgressBar";
import Badge from "../ui/Badge";
import { useUpload } from "../../../store/upload";

function UploadItem({
  file,
}) {
  const removeFile = useUpload(
    (state) => state.removeFile
  );
  const uploadFile = useUpload(
    (state) => state.uploadFile
  );

  const formatSize = (bytes) => {
    if (bytes < 1024)
      return `${bytes} B`;

    if (bytes < 1024 * 1024)
      return `${(bytes / 1024).toFixed(1)} KB`;

    return `${(
      bytes /
      (1024 * 1024)
    ).toFixed(2)} MB`;
  };

  const statusConfig = {
    selected: {
      badge: "neutral",
      label: "Ready to upload",
      icon: <Upload size={14} />,
    },
    processing: {
      badge: "warning",
      label: "Uploading...",
      icon: <LoaderCircle size={14} className="animate-spin" />,
    },
    completed: {
      badge: "success",
      label: "Ready",
      icon: <CheckCircle2 size={14} />,
    },
    error: {
      badge: "error",
      label: "Failed",
      icon: null,
    },
  };

  const currentStatus = statusConfig[file.status] || statusConfig.selected;

  return (
    <div className="rounded-2xl border border-border bg-surface p-4 transition-all hover:border-primary/30">
      <div className="flex items-start justify-between gap-3">
        <div className="flex gap-3 flex-1 min-w-0">
          <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10">
            <FileText
              size={22}
              className="text-primary"
            />
          </div>

          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-1 font-medium text-text">
              {file.name}
            </h3>

            <div className="mt-2 flex flex-wrap items-center gap-2">
              <p className="text-xs text-textMuted">
                {formatSize(file.size)}
              </p>

              {file.pages && (
                <span className="text-xs text-textMuted">
                  • {file.pages} page{file.pages !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          </div>
        </div>

        <button
          onClick={() => removeFile(file.id)}
          className="flex-shrink-0 rounded-lg p-2 text-textMuted transition hover:bg-background hover:text-error"
          title="Remove file"
        >
          <Trash2 size={18} />
        </button>
      </div>

      {file.status === "processing" && (
        <div className="mt-4">
          <ProgressBar value={file.progress || 0} />
        </div>
      )}

      <div className="mt-4 flex items-center justify-between">
        <Badge variant={currentStatus.badge} className="inline-flex items-center gap-1.5">
          {currentStatus.icon}
          {currentStatus.label}
        </Badge>

        {file.error && (
          <span className="text-xs text-error font-medium">{file.error}</span>
        )}
      </div>
    </div>
  );
}

export default UploadItem;