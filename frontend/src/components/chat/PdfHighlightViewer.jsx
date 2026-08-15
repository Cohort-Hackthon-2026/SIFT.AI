import { useEffect, useRef, useState, useCallback } from "react";
import * as pdfjsLib from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Download, AlertCircle, Loader2 } from "lucide-react";
import { api } from "../../lib/api";

// Configure PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;

export default function PdfHighlightViewer({
  documentId,
  documentName,
  pageNumber = 1,
  boundingBoxes = [],
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [pdfDoc, setPdfDoc] = useState(null);
  const [currentPage, setCurrentPage] = useState(pageNumber);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.0);
  const [loading, setLoading] = useState(true);
  const [renderLoading, setRenderLoading] = useState(false);
  const [error, setError] = useState(null);
  const [viewportDims, setViewportDims] = useState({ width: 0, height: 0, scale: 1 });
  const renderTaskRef = useRef(null);

  // Sync page when prop changes
  useEffect(() => {
    if (pageNumber && pageNumber !== currentPage) {
      setCurrentPage(pageNumber);
    }
  }, [pageNumber]);

  // Load PDF data
  useEffect(() => {
    let active = true;

    async function loadPdf() {
      if (!documentId || String(documentId).startsWith("chat-text-")) {
        setError("This source is a text statement, not a PDF document.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const blob = await api.getDocumentFile(documentId);
        if (!active) return;
        const arrayBuffer = await blob.arrayBuffer();
        if (!active) return;

        const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
        const doc = await loadingTask.promise;
        if (!active) return;

        setPdfDoc(doc);
        setTotalPages(doc.numPages);
        setCurrentPage(Math.min(Math.max(1, pageNumber), doc.numPages));
      } catch (err) {
        if (!active) return;
        console.error("Failed to load PDF document:", err);
        setError("Could not load PDF document file.");
      } finally {
        if (active) setLoading(false);
      }
    }

    loadPdf();

    return () => {
      active = false;
    };
  }, [documentId]);

  // Render Page to Canvas
  const renderPage = useCallback(async () => {
    if (!pdfDoc || !canvasRef.current || currentPage < 1) return;

    // Cancel any previous render in flight
    if (renderTaskRef.current) {
      try {
        renderTaskRef.current.cancel();
      } catch {
        // ignore cancellation error
      }
    }

    setRenderLoading(true);

    try {
      const page = await pdfDoc.getPage(currentPage);
      const canvas = canvasRef.current;
      if (!canvas) return;

      const containerWidth = containerRef.current?.clientWidth || 450;
      const unscaledViewport = page.getViewport({ scale: 1.0 });
      // Calculate responsive base scale to fit container width comfortably
      const targetBaseScale = Math.min(1.5, (containerWidth - 24) / unscaledViewport.width);
      const computedScale = targetBaseScale * scale;
      const viewport = page.getViewport({ scale: computedScale });

      const pixelRatio = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * pixelRatio);
      canvas.height = Math.floor(viewport.height * pixelRatio);
      canvas.style.width = `${Math.floor(viewport.width)}px`;
      canvas.style.height = `${Math.floor(viewport.height)}px`;

      const ctx = canvas.getContext("2d");
      ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

      const renderContext = {
        canvasContext: ctx,
        viewport,
      };

      const task = page.render(renderContext);
      renderTaskRef.current = task;
      await task.promise;

      setViewportDims({
        width: viewport.width,
        height: viewport.height,
        scale: computedScale,
        originalWidth: unscaledViewport.width,
        originalHeight: unscaledViewport.height,
      });
    } catch (err) {
      if (err?.name !== "RenderingCancelledException") {
        console.error("Error rendering PDF page:", err);
      }
    } finally {
      setRenderLoading(false);
    }
  }, [pdfDoc, currentPage, scale]);

  useEffect(() => {
    renderPage();
  }, [renderPage]);

  // Download PDF
  const handleDownload = async () => {
    try {
      const blob = await api.getDocumentFile(documentId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = documentName || "document.pdf";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (_err) {
      window.addToast?.("Failed to download PDF", "error");
    }
  };

  if (loading) {
    return (
      <div className="flex h-72 flex-col items-center justify-center gap-3 rounded-2xl border border-border bg-background/50 p-6 text-center">
        <Loader2 size={28} className="animate-spin text-primary" />
        <p className="text-sm font-medium text-text">Loading PDF evidence...</p>
        <p className="text-xs text-textMuted">{documentName}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-2xl border border-error/30 bg-error/5 p-6 text-center">
        <AlertCircle size={28} className="text-error" />
        <p className="text-sm font-medium text-text">{error}</p>
        <p className="text-xs text-textMuted">You can still read the extracted text transcript below.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-3">
      {/* Viewer Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-background p-2 text-xs font-medium text-text shadow-sm">
        {/* Page Nav */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            disabled={currentPage <= 1}
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            className="rounded-lg p-1.5 hover:bg-surface disabled:opacity-40 transition"
            title="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="px-2 font-mono">
            Page {currentPage} / {totalPages || 1}
          </span>
          <button
            type="button"
            disabled={currentPage >= totalPages}
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            className="rounded-lg p-1.5 hover:bg-surface disabled:opacity-40 transition"
            title="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Zoom & Download Actions */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            disabled={scale <= 0.75}
            onClick={() => setScale((s) => Math.max(0.6, s - 0.2))}
            className="rounded-lg p-1.5 hover:bg-surface disabled:opacity-40 transition"
            title="Zoom out"
          >
            <ZoomOut size={16} />
          </button>
          <span className="w-10 text-center font-mono text-[11px]">
            {Math.round(scale * 100)}%
          </span>
          <button
            type="button"
            disabled={scale >= 2.0}
            onClick={() => setScale((s) => Math.min(2.0, s + 0.2))}
            className="rounded-lg p-1.5 hover:bg-surface disabled:opacity-40 transition"
            title="Zoom in"
          >
            <ZoomIn size={16} />
          </button>
          <div className="h-4 w-px bg-border mx-1" />
          <button
            type="button"
            onClick={handleDownload}
            className="flex items-center gap-1 rounded-lg px-2 py-1 hover:bg-surface transition text-primary"
            title="Download original PDF"
          >
            <Download size={14} />
            <span className="hidden sm:inline">PDF</span>
          </button>
        </div>
      </div>

      {/* Canvas Container with Highlight Overlays */}
      <div
        ref={containerRef}
        className="relative flex justify-center overflow-auto rounded-2xl border border-border bg-slate-900/5 dark:bg-black/30 p-3 min-h-[350px]"
      >
        <div
          className="relative shadow-xl rounded-sm"
          style={{
            width: viewportDims.width || "auto",
            height: viewportDims.height || "auto",
          }}
        >
          <canvas ref={canvasRef} className="block rounded-sm bg-white" />

          {/* Render Bounding-Box Highlight Rectangles for this Page */}
          {currentPage === pageNumber &&
            boundingBoxes &&
            boundingBoxes.length > 0 &&
            viewportDims.scale > 0 &&
            boundingBoxes.map((box, index) => {
              // Convert point coordinates [x0, y0, x1, y1] to scaled pixels
              const left = (box.x0 || 0) * viewportDims.scale;
              const top = (box.y0 || 0) * viewportDims.scale;
              const width = ((box.x1 || 0) - (box.x0 || 0)) * viewportDims.scale;
              const height = ((box.y1 || 0) - (box.y0 || 0)) * viewportDims.scale;

              if (width <= 0 || height <= 0) return null;

              return (
                <div
                  key={`highlight-${index}`}
                  style={{
                    position: "absolute",
                    left: `${left}px`,
                    top: `${top}px`,
                    width: `${width}px`,
                    height: `${height}px`,
                    backgroundColor: "rgba(245, 158, 11, 0.32)",
                    border: "1.5px solid rgba(217, 119, 6, 0.85)",
                    borderRadius: "3px",
                    boxShadow: "0 0 10px rgba(245, 158, 11, 0.45)",
                    pointerEvents: "none",
                    transition: "all 0.2s ease",
                  }}
                  title="Source Evidence Grounding"
                />
              );
            })}
        </div>
      </div>

      {boundingBoxes.length > 0 && currentPage === pageNumber && (
        <div className="flex items-center gap-1.5 text-[11px] text-amber-600 dark:text-amber-400 font-medium px-1">
          <div className="h-2.5 w-2.5 rounded-sm bg-amber-500/40 border border-amber-600" />
          <span>Yellow highlight indicates exact paragraph coordinates cited by SIFT.AI</span>
        </div>
      )}
    </div>
  );
}
