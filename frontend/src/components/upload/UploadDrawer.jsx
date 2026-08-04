import { X } from "lucide-react";

import DropZone from "./DropZone";
import UploadItem from "./UploadItem";

import { useUpload } from "../../../store/upload";

function UploadDrawer() {
    const drawerOpen = useUpload(
        (state) => state.drawerOpen
    );

    const closeDrawer = useUpload(
        (state) => state.closeDrawer
    );

    const files = useUpload(
        (state) => state.files
    );

    if (!drawerOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-overlay p-4 backdrop-blur-sm">

            <div className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-3xl border border-border bg-surface shadow-2xl">

                <div className="flex items-center justify-between border-b border-border p-6">

                    <div>

                        <h2 className="text-xl font-semibold text-text">
                            Upload Documents
                        </h2>

                        <p className="mt-1 text-sm text-textMuted">
                            Add PDFs to your knowledge base.
                        </p>

                    </div>

                    <button
                        onClick={closeDrawer}
                        className="rounded-xl p-2 transition hover:bg-background"
                    >
                        <X size={20} />
                    </button>

                </div>

                <div className="space-y-6 overflow-y-auto p-6">

                    <DropZone />

                    {files.length > 0 && (
                        <div className="space-y-4">

                            {files.map((file) => (
                                <UploadItem
                                    key={file.id}
                                    file={file}
                                />
                            ))}

                        </div>
                    )}

                </div>

            </div>

        </div>
    );
}

export default UploadDrawer;
