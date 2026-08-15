import React, { useState, useRef, useEffect } from "react";
import { ChevronDown, Check } from "lucide-react";
import "./select.css";

export default function Select({ value, onChange, options = [], placeholder, className = "" }) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);
  const buttonRef = useRef(null);

  useEffect(() => {
    function onDocClick(e) {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    function onKey(e) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("touchstart", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("touchstart", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const selected = options.find((o) => o.value === value);

  return (
    <div className={`sift-select-custom ${className}`} ref={containerRef}>
      {open && <div className="sift-select-overlay" onClick={() => setOpen(false)} />}

      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        className="sift-select-trigger"
        onClick={() => setOpen((v) => !v)}
      >
        <span className={`sift-select-value ${!selected ? 'muted' : ''}`}>{selected?.label ?? placeholder ?? "Select"}</span>
        <ChevronDown size={16} className="sift-select-chevron" />
      </button>

      <div className={`sift-select-menu ${open ? 'open' : ''}`} role="listbox" tabIndex={-1}>
        {options.map((opt) => (
          <div
            key={opt.value}
            role="option"
            aria-selected={opt.value === value}
            className={`sift-select-item ${opt.value === value ? 'selected' : ''}`}
            onClick={() => {
              onChange && onChange(opt.value);
              setOpen(false);
            }}
          >
            <span className="sift-select-item-label">{opt.label}</span>
            {opt.value === value && (
              <Check size={16} className="sift-select-item-check" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
