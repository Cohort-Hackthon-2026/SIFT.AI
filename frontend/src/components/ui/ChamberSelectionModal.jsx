import React, { useState } from "react";
import { useUI } from "../../../store/ui";
import { useProfile } from "../../../store/profile";
import { api } from "../../lib/api";
import { Check, Plus, LogIn } from "lucide-react";

export default function ChamberSelectionModal() {
  const { chamberSelectionModalOpen, closeChamberSelectionModal } = useUI();
  const { fetchProfile } = useProfile();
  const [mode, setMode] = useState("choice"); // "choice", "create", "join"
  const [chamberName, setChamberName] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!chamberSelectionModalOpen) return null;

  const handleCreate = async () => {
    if (!chamberName.trim()) {
      setError("Please enter a chamber name");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await api.createChambers(chamberName);
      // Re-fetch profile to sync chambers_id
      await fetchProfile();
      closeChamberSelectionModal();
    } catch (err) {
      setError(err.message || "Failed to create chamber");
    } finally {
      setLoading(false);
    }
  };

  const handleJoin = async () => {
    if (!inviteCode.trim()) {
      setError("Please enter an invite code");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await api.joinChambers(inviteCode);
      // Re-fetch profile to sync chambers_id
      await fetchProfile();
      closeChamberSelectionModal();
    } catch (err) {
      setError(err.message || "Failed to join chamber");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "color-mix(in srgb, var(--background, #000) 70%, transparent)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        zIndex: 9999,
        pointerEvents: "auto",
        padding: "16px",
      }}
    >
      <div
        style={{
          width: 440,
          maxWidth: "100%",
          background: "var(--surface, #ffffff)",
          borderRadius: 20,
          padding: "32px 28px",
          boxShadow:
            "0 20px 40px -15px rgba(0, 0, 0, 0.15), 0 0 0 1px color-mix(in srgb, var(--text, #000) 8%, transparent)",
          color: "var(--text)",
          zIndex: 10000,
          fontFamily:
            'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        }}
      >
        {/* Header Icon */}
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: "color-mix(in srgb, var(--primary, #0066ff) 12%, transparent)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 20,
            color: "var(--primary, #0066ff)",
          }}
        >
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
        </div>

        {mode === "choice" && (
          <>
            <h2
              style={{
                margin: 0,
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                lineHeight: 1.2,
              }}
            >
              Create or join a chamber
            </h2>
            <p
              style={{
                marginTop: 8,
                marginBottom: 0,
                color: "var(--text-muted, #666)",
                fontSize: 14,
                lineHeight: 1.5,
              }}
            >
              Billing in SIFT.AI is per-chamber. You'll need to create or join one to subscribe.
            </p>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 12,
                marginTop: 24,
              }}
            >
              <button
                type="button"
                onClick={() => {
                  setMode("create");
                  setError(null);
                }}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "14px 16px",
                  background: "color-mix(in srgb, var(--primary) 12%, transparent)",
                  border: "1px solid color-mix(in srgb, var(--primary) 30%, transparent)",
                  borderRadius: 12,
                  color: "var(--primary)",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: 14,
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "color-mix(in srgb, var(--primary) 18%, transparent)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "color-mix(in srgb, var(--primary) 12%, transparent)";
                }}
              >
                <Plus size={18} />
                Create a new chamber
              </button>

              <button
                type="button"
                onClick={() => {
                  setMode("join");
                  setError(null);
                }}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "14px 16px",
                  background: "color-mix(in srgb, var(--primary) 8%, transparent)",
                  border: "1px solid color-mix(in srgb, var(--primary) 20%, transparent)",
                  borderRadius: 12,
                  color: "var(--text)",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: 14,
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "color-mix(in srgb, var(--primary) 14%, transparent)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "color-mix(in srgb, var(--primary) 8%, transparent)";
                }}
              >
                <LogIn size={18} />
                Join with invite code
              </button>
            </div>
          </>
        )}

        {mode === "create" && (
          <>
            <h2
              style={{
                margin: 0,
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                lineHeight: 1.2,
              }}
            >
              Create a chamber
            </h2>
            <p
              style={{
                marginTop: 8,
                marginBottom: 0,
                color: "var(--text-muted, #666)",
                fontSize: 14,
                lineHeight: 1.5,
              }}
            >
              Enter your law firm or team name. You'll be the principal.
            </p>

            <input
              type="text"
              placeholder="e.g., John & Associates LLP"
              value={chamberName}
              onChange={(e) => setChamberName(e.target.value)}
              disabled={loading}
              style={{
                marginTop: 20,
                width: "100%",
                padding: "10px 14px",
                border: "1px solid var(--border)",
                borderRadius: 10,
                fontSize: 14,
                background: "var(--surface)",
                color: "var(--text)",
                boxSizing: "border-box",
              }}
            />

            {error && (
              <div style={{ marginTop: 12, padding: "10px 12px", background: "color-mix(in srgb, #ff4444 12%, transparent)", borderRadius: 8, fontSize: 13, color: "#ff4444" }}>
                {error}
              </div>
            )}

            <div
              style={{
                display: "flex",
                gap: 12,
                justifyContent: "space-between",
                marginTop: 24,
              }}
            >
              <button
                type="button"
                onClick={() => {
                  setMode("choice");
                  setError(null);
                  setChamberName("");
                }}
                disabled={loading}
                style={{
                  flex: 1,
                  padding: "12px 16px",
                  border: "1px solid var(--border)",
                  background: "var(--surface)",
                  borderRadius: 12,
                  color: "var(--text)",
                  cursor: loading ? "not-allowed" : "pointer",
                  fontWeight: 600,
                  fontSize: 14,
                  opacity: loading ? 0.7 : 1,
                }}
              >
                Back
              </button>
              <button
                type="button"
                onClick={handleCreate}
                disabled={loading}
                style={{
                  flex: 1,
                  padding: "12px 16px",
                  background: "var(--primary, #0066ff)",
                  color: "var(--text-inverse, #ffffff)",
                  border: "none",
                  borderRadius: 12,
                  cursor: loading ? "not-allowed" : "pointer",
                  fontWeight: 600,
                  fontSize: 14,
                  opacity: loading ? 0.7 : 1,
                  transition: "all 0.15s ease",
                }}
              >
                {loading ? "Creating..." : "Create"}
              </button>
            </div>
          </>
        )}

        {mode === "join" && (
          <>
            <h2
              style={{
                margin: 0,
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                lineHeight: 1.2,
              }}
            >
              Join a chamber
            </h2>
            <p
              style={{
                marginTop: 8,
                marginBottom: 0,
                color: "var(--text-muted, #666)",
                fontSize: 14,
                lineHeight: 1.5,
              }}
            >
              Ask your principal or partner for the invite code to join their chamber.
            </p>

            <input
              type="text"
              placeholder="Invite code"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
              disabled={loading}
              style={{
                marginTop: 20,
                width: "100%",
                padding: "10px 14px",
                border: "1px solid var(--border)",
                borderRadius: 10,
                fontSize: 14,
                background: "var(--surface)",
                color: "var(--text)",
                boxSizing: "border-box",
                fontFamily: "monospace",
              }}
            />

            {error && (
              <div style={{ marginTop: 12, padding: "10px 12px", background: "color-mix(in srgb, #ff4444 12%, transparent)", borderRadius: 8, fontSize: 13, color: "#ff4444" }}>
                {error}
              </div>
            )}

            <div
              style={{
                display: "flex",
                gap: 12,
                justifyContent: "space-between",
                marginTop: 24,
              }}
            >
              <button
                type="button"
                onClick={() => {
                  setMode("choice");
                  setError(null);
                  setInviteCode("");
                }}
                disabled={loading}
                style={{
                  flex: 1,
                  padding: "12px 16px",
                  border: "1px solid var(--border)",
                  background: "var(--surface)",
                  borderRadius: 12,
                  color: "var(--text)",
                  cursor: loading ? "not-allowed" : "pointer",
                  fontWeight: 600,
                  fontSize: 14,
                  opacity: loading ? 0.7 : 1,
                }}
              >
                Back
              </button>
              <button
                type="button"
                onClick={handleJoin}
                disabled={loading}
                style={{
                  flex: 1,
                  padding: "12px 16px",
                  background: "var(--primary, #0066ff)",
                  color: "var(--text-inverse, #ffffff)",
                  border: "none",
                  borderRadius: 12,
                  cursor: loading ? "not-allowed" : "pointer",
                  fontWeight: 600,
                  fontSize: 14,
                  opacity: loading ? 0.7 : 1,
                  transition: "all 0.15s ease",
                }}
              >
                {loading ? "Joining..." : "Join"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
