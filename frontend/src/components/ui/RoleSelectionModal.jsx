import React, { useState, useEffect } from "react";
import { useUI } from "../../../store/ui";
import { useProfile } from "../../../store/profile";
import Select from "./Select";

export default function RoleSelectionModal() {
  const { roleSelectionModalOpen, closeRoleSelectionModal } = useUI();
  const { profile, updateProfile, loading } = useProfile();
  const [role, setRole] = useState("");

  useEffect(() => {
    if (profile?.role) {
      setRole(profile.role);
    }
  }, [profile?.role]);

  if (!roleSelectionModalOpen) return null;

  const roles = [
    { value: "PRINCIPAL", label: "Principal" },
    { value: "PARTNER", label: "Partner" },
    { value: "ASSOCIATE", label: "Associate" },
    { value: "TRAINEE", label: "Trainee" },
    { value: "LAW_STUDENT", label: "Law Student" },
    { value: "SAN", label: "SAN" },
  ];

  const handleSave = async () => {
    if (!role) {
      alert("Please select a role");
      return;
    }
    try {
      await updateProfile({ role });
      // Re-fetch profile to ensure chambers_id is in sync
      await new Promise(r => setTimeout(r, 100));
      closeRoleSelectionModal();
    } catch (err) {
      alert("Failed to update role: " + (err.message || String(err)));
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
        /* Overlay uses CSS color-mix to create a semi-transparent version of var(--background) */
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
        {/* Header Icon / Badge Visual (Optional structural polish) */}
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background:
              "color-mix(in srgb, var(--primary, #0066ff) 12%, transparent)",
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
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </div>

        <h2
          style={{
            margin: 0,
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: "-0.02em",
            lineHeight: 1.2,
          }}
        >
          Select your role
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
          Choose your professional role to complete your profile setup. You can
          change this later in settings.
        </p>

        <div style={{ marginTop: 24 }}>
          <label
            style={{
              display: "block",
              fontSize: 13,
              fontWeight: 600,
              letterSpacing: "0.01em",
              color: "var(--text)",
              marginBottom: 8,
            }}
          >
            Role
          </label>
          <Select
            value={role}
            onChange={setRole}
            options={roles}
            placeholder="Select your role"
          />
        </div>

        <div
          style={{
            display: "flex",
            gap: 12,
            justifyContent: "flex-end",
            marginTop: 32,
          }}
        >
          <button
            disabled={loading}
            onClick={handleSave}
            style={{
              width: "100%",
              background: "var(--primary, #0066ff)",
              color: "var(--text-inverse, #ffffff)",
              border: "none",
              padding: "12px 20px",
              borderRadius: 12,
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1,
              transition: "all 0.15s ease",
              boxShadow:
                "0 4px 12px color-mix(in srgb, var(--primary, #0066ff) 30%, transparent)",
            }}
          >
            {loading ? "Saving..." : "Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}