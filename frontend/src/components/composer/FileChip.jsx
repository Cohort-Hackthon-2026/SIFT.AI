import { FileText, X } from "lucide-react";

import { useUpload } from "../../../store/upload";

function FileChip({ file }) {
  const removeFile = useUpload((state) => state.removeFile);

  return (
    <div className="flex items-center gap-2 rounded-full border border-border bg-background px-3 py-2">

      <FileText
        size={16}
        className="text-primary"
      />

      <span className="max-w-[140px] truncate text-sm">
        {file.name}
      </span>

      <button
        onClick={() => removeFile(file.id)}
      >
        <X
          size={16}
          className="text-textMuted hover:text-text"
        />
      </button>

    </div>
  );
}

export default FileChip;