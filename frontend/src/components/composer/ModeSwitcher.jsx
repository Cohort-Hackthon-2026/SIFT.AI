import { useSettings } from "../../../store/settings";

function ModeSwitcher() {
  const mode = useSettings((state) => state.mode);
  const setMode = useSettings((state) => state.setMode);

  return (
    <div className="flex rounded-xl border border-border bg-background p-1">

      <button
        onClick={() => setMode("STRICT")}
        className={`rounded-lg px-4 py-2 text-sm transition ${
          mode === "STRICT"
            ? "bg-primary text-textInverse"
            : "text-textMuted"
        }`}
      >
        STRICT
      </button>

      <button
        onClick={() => setMode("ENHANCED")}
        className={`rounded-lg px-4 py-2 text-sm transition ${
          mode === "ENHANCED"
            ? "bg-primary text-textInverse"
            : "text-textMuted"
        }`}
      >
        ENHANCED
      </button>

    </div>
  );
}

export default ModeSwitcher;