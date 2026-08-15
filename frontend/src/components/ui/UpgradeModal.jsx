import React from "react";
import { useUI } from "../../../store/ui";

export default function UpgradeModal() {
  const { upgradeModalOpen, upgradeModalDetail, closeUpgradeModal } = useUI();

  if (!upgradeModalOpen) return null;

  const required = upgradeModalDetail?.upgrade_required || null;
  const message = upgradeModalDetail?.message || "This action requires an upgraded plan.";

  return (
    <div style={{ position: "fixed", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.4)", zIndex: 1200 }}>
      <div style={{ width: 520, maxWidth: '94%', background: 'var(--surface)', borderRadius: 12, padding: 20, boxShadow: '0 8px 32px rgba(0,0,0,0.2)', color: 'var(--text)' }}>
        <h3 style={{ margin: 0 }}>Upgrade required</h3>
        <p style={{ color: 'var(--text-muted)' }}>{message}</p>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
          <button onClick={closeUpgradeModal} style={{ background: 'transparent', border: '1px solid var(--border)', padding: '8px 12px', borderRadius: 8 }}>Close</button>
          <button onClick={() => { closeUpgradeModal(); window.location.href = '/settings?open=billing'; }} style={{ background: 'var(--primary)', color: 'var(--text-inverse)', border: 'none', padding: '8px 12px', borderRadius: 8 }}>Upgrade to {required || 'a paid plan'}</button>
        </div>
      </div>
    </div>
  );
}
