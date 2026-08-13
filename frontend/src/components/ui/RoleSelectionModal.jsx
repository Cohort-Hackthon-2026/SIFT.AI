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
      closeRoleSelectionModal();
    } catch (err) {
      alert("Failed to update role: " + (err.message || String(err)));
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.5)", zIndex: 1300 }}>
      <div style={{ width: 480, maxWidth: "94%", background: "var(--surface)", borderRadius: 12, padding: 24, boxShadow: "0 20px 48px rgba(0,0,0,0.3)", color: "var(--text)" }}>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>Select your role</h2>
        <p style={{ marginTop: 8, color: "var(--text-muted)", fontSize: 14 }}>
          Choose your professional role to complete your profile setup. You can change this later in settings.
        </p>

        <div style={{ marginTop: 20 }}>
          <label style={{ display: "block", fontSize: 14, color: "var(--text-muted)", marginBottom: 8 }}>
            Role
          </label>
          <Select value={role} onChange={setRole} options={roles} placeholder="Select your role" />
        </div>

        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", marginTop: 24 }}>
          <button
            disabled={loading}
            onClick={handleSave}
            style={{
              background: "var(--primary)",
              color: "var(--text-inverse)",
              border: "none",
              padding: "10px 16px",
              borderRadius: 8,
              fontWeight: 500,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? "Saving..." : "Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
