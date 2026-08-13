import React from "react";
import "./select.css";

export default function Select({ value, onChange, options = [], placeholder, className = "" }) {
  return (
    <div className={`sift-select ${className}`}>
      <select value={value || ""} onChange={(e) => onChange && onChange(e.target.value)}>
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      <div className="sift-select-arrow">▾</div>
    </div>
  );
}
