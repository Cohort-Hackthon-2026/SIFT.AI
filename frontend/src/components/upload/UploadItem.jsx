import {
  FileText,
  Trash2,
  CheckCircle2,
  LoaderCircle,
} from "lucide-react";

import ProgressBar from "./ProgressBar";
import { useUpload } from "../../../store/upload";

function UploadItem({
  file,
}) {
  const removeFile = useUpload(
    (state) => state.removeFile
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

  return (
    <div className="rounded-2xl border border-border bg-surface p-4">

      <div className="flex items-start justify-between">

        <div className="flex gap-3">

          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">

            <FileText
              size={22}
              className="text-primary"
            />

          </div>

          <div>

            <h3 className="line-clamp-1 font-medium">

              {file.name}

            </h3>

            <p className="mt-1 text-sm text-textMuted">

              {formatSize(file.size)}

            </p>

          </div>

        </div>

        <button
          onClick={() =>
            removeFile(file.id)
          }
          className="rounded-lg p-2 text-textMuted transition hover:bg-background hover:text-error"
        >
          <Trash2 size={18} />
        </button>

      </div>

      {/* <div className="mt-5">

        <ProgressBar
          value={file.progress}
        />

      </div> */}

      <div className="mt-4 flex items-center justify-between">

        <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
          Selected
        </span>

        <span className="text-sm text-textMuted">
          {formatSize(file.size)}
        </span>

      </div>

      <div className="mt-3 flex items-center justify-between text-sm">

        <span className="text-textMuted">

          {file.progress}%

        </span>

        {file.status ===
          "processing" ? (
          <div className="flex items-center gap-2 text-primary">

            <LoaderCircle
              size={15}
              className="animate-spin"
            />

            Processing...

          </div>
        ) : file.status ===
          "completed" ? (
          <div className="flex items-center gap-2 text-primary">

            <CheckCircle2
              size={15}
            />

            Ready

          </div>
        ) : (
          <span className="text-textMuted">

            Waiting

          </span>
        )}

      </div>

    </div>
  );
}

export default UploadItem;