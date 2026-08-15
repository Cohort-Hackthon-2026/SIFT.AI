import { useState } from "react";
import { useUI } from "../../../store/ui";
import { useProfile } from "../../../store/profile";
import Select from "./Select";
import { Scale, ShieldCheck, Globe, X } from "lucide-react";

export default function RoleSelectionModal() {
  const { roleSelectionModalOpen, closeRoleSelectionModal } = useUI();
  const { profile, updateProfile, loading } = useProfile();
  const [role, setRole] = useState(profile?.role || "");
  const [nbaNumber, setNbaNumber] = useState(profile?.nba_number || "");
  const [defaultJurisdiction, setDefaultJurisdiction] = useState(profile?.default_jurisdiction || "NG");

  if (!roleSelectionModalOpen) return null;

  const roles = [
    { value: "PRINCIPAL", label: "Principal Partner" },
    { value: "PARTNER", label: "Partner" },
    { value: "ASSOCIATE", label: "Associate Counsel" },
    { value: "TRAINEE", label: "NYSC Legal Trainee / Pupil" },
    { value: "LAW_STUDENT", label: "Law Student / Researcher" },
    { value: "SAN", label: "Senior Advocate of Nigeria (SAN)" },
  ];

  const jurisdictions = [
    { value: "NG", label: "🇳🇬 Nigeria (Federal & State Courts)" },
    { value: "UK", label: "🇬🇧 United Kingdom (Common Law)" },
    { value: "US", label: "🇺🇸 United States" },
    { value: "GH", label: "🇬🇭 Ghana" },
  ];

  const handleSave = async () => {
    if (!role) {
      alert("Please select your professional role to continue.");
      return;
    }
    try {
      await updateProfile({
        role,
        nba_number: nbaNumber.trim() || null,
        default_jurisdiction: defaultJurisdiction || "NG",
      });
      // Small pause to ensure profile store state settles
      await new Promise((r) => setTimeout(r, 100));
      closeRoleSelectionModal();
    } catch (err) {
      alert("Failed to update profile: " + (err.message || String(err)));
    }
  };

  return (
    <div
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) closeRoleSelectionModal();
      }}
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "color-mix(in srgb, var(--background, #000) 75%, transparent)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        zIndex: 9999,
        pointerEvents: "auto",
        padding: "16px",
      }}
    >
      <div
        style={{
          width: 480,
          maxWidth: "100%",
          background: "var(--surface, #ffffff)",
          borderRadius: 24,
          padding: "32px 28px",
          boxShadow:
            "0 24px 48px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px color-mix(in srgb, var(--border, #e2e8f0) 80%, transparent)",
          color: "var(--text)",
          zIndex: 10000,
          fontFamily:
            'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        }}
      >
        {/* Close Button */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
          <button
            type="button"
            onClick={closeRoleSelectionModal}
            disabled={loading}
            aria-label="Close"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 32,
              height: 32,
              borderRadius: 10,
              border: "1px solid var(--border, #e2e8f0)",
              background: "transparent",
              color: "var(--text-muted, #999)",
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.5 : 1,
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "var(--background, #f1f5f9)"; e.currentTarget.style.color = "var(--text)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--text-muted, #999)"; }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Header Icon & Title */}
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 14,
              background: "color-mix(in srgb, var(--primary, #0066ff) 14%, transparent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--primary, #0066ff)",
              flexShrink: 0,
            }}
          >
            <Scale size={24} />
          </div>
          <div>
            <h2
              style={{
                margin: 0,
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                lineHeight: 1.2,
              }}
            >
              Legal Practitioner Profile
            </h2>
            <p
              style={{
                margin: "4px 0 0 0",
                color: "var(--text-muted, #666)",
                fontSize: 13,
                lineHeight: 1.4,
              }}
            >
              Tailor research precision, court citation standards, and chambers permissions.
            </p>
          </div>
        </div>

        {/* Role Selection */}
        <div style={{ marginTop: 20 }}>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 13,
              fontWeight: 600,
              color: "var(--text)",
              marginBottom: 6,
            }}
          >
            Professional Role <span style={{ color: "var(--primary)" }}>*</span>
          </label>
          <Select
            value={role}
            onChange={setRole}
            options={roles}
            placeholder="Select your role (e.g. Associate, SAN, Partner)"
          />
        </div>

        {/* NBA Enrolment Number */}
        <div style={{ marginTop: 18 }}>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 13,
              fontWeight: 600,
              color: "var(--text)",
              marginBottom: 6,
            }}
          >
            <ShieldCheck size={14} style={{ color: "var(--text-muted)" }} />
            NBA Enrolment / Bar Number
            <span style={{ fontSize: 11, fontWeight: 400, color: "var(--text-muted)" }}>(Optional)</span>
          </label>
          <input
            type="text"
            value={nbaNumber}
            onChange={(e) => setNbaNumber(e.target.value)}
            placeholder="e.g. SCN/012345 or NBA-LAG-2024"
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "10px 14px",
              borderRadius: 12,
              border: "1px solid color-mix(in srgb, var(--border, #e2e8f0) 90%, transparent)",
              background: "var(--background, #f8fafc)",
              color: "var(--text)",
              fontSize: 14,
              outline: "none",
              transition: "border-color 0.15s ease",
            }}
          />
          <span style={{ display: "block", marginTop: 4, fontSize: 11, color: "var(--text-muted)" }}>
            Used for chambers verification and formal memo letterhead exports.
          </span>
        </div>

        {/* Default Jurisdiction */}
        <div style={{ marginTop: 18 }}>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 13,
              fontWeight: 600,
              color: "var(--text)",
              marginBottom: 6,
            }}
          >
            <Globe size={14} style={{ color: "var(--text-muted)" }} />
            Primary Legal Jurisdiction
          </label>
          <Select
            value={defaultJurisdiction}
            onChange={setDefaultJurisdiction}
            options={jurisdictions}
            placeholder="Select Jurisdiction"
          />
        </div>

        {/* Action Buttons */}
        <div
          style={{
            display: "flex",
            gap: 12,
            justifyContent: "flex-end",
            marginTop: 28,
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
              padding: "13px 20px",
              borderRadius: 14,
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1,
              transition: "all 0.15s ease",
              boxShadow:
                "0 4px 16px color-mix(in srgb, var(--primary, #0066ff) 35%, transparent)",
            }}
          >
            {loading ? "Saving Profile..." : "Complete Setup"}
          </button>
        </div>
      </div>
    </div>
  );
}