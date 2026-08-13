import { useEffect, useState } from "react";
import { Circle, CircleCheck, Play, Settings2, Square } from "lucide-react";
import { useBilling } from "../../store/billing";
import { useUI } from "../../store/ui";

import MainLayout from "../components/layout/MainLayout";
import { useSettings } from "../../store/settings";
import { useProfile } from "../../store/profile";
import Select from "../components/ui/Select";
import { SPEECH_PREVIEW, speakText } from "../lib/speech";

function Settings() {
  const voices = useSettings((state) => state.voices);
  const selectedVoice = useSettings((state) => state.voice);
  const setVoice = useSettings((state) => state.setVoice);
  const [previewing, setPreviewing] = useState(null);

  useEffect(() => () => window.speechSynthesis?.cancel(), []);

  const preview = (voice) => {
    if (previewing === voice.value) {
      window.speechSynthesis.cancel();
      setPreviewing(null);
      return;
    }
    setPreviewing(voice.value);
    speakText(SPEECH_PREVIEW, voice.value, voice, () => setPreviewing(null));
  };

  return (
    <MainLayout>
      <section className="mx-auto w-full max-w-4xl py-2 sm:py-6">
        <div className="mb-6 flex items-start gap-4 sm:mb-8">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Settings2 size={24} />
          </div>
          <div>
            <h2 className="text-2xl font-semibold text-text sm:text-3xl">Settings</h2>
            <p className="mt-2 max-w-2xl text-sm text-textMuted sm:text-base">
              Choose the voice used when reading chats and responses aloud. Your selection is saved on this device.
            </p>
          </div>
        </div>

        <div className="rounded-3xl border border-border bg-surface p-4 shadow-sm sm:p-6">
          <div className="mb-5">
            <h3 className="text-lg font-semibold text-text">Reading voice</h3>
            <p className="mt-1 text-sm text-textMuted">Select a voice or play a short preview before deciding.</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {voices.map((voice) => {
              const selected = selectedVoice === voice.value;
              const playing = previewing === voice.value;
              return (
                <div key={voice.value} className={`flex min-w-0 items-center gap-3 rounded-2xl border p-3 transition sm:p-4 ${selected ? "border-primary bg-primary/10" : "border-border bg-background/60 hover:border-primary/50"}`}>
                  <button type="button" onClick={() => setVoice(voice.value)} className="flex min-w-0 flex-1 items-start gap-3 text-left" aria-pressed={selected}>
                    <span className="mt-0.5 shrink-0 text-primary" aria-hidden="true">
                      {selected ? <CircleCheck size={21} fill="currentColor" className="text-primary [&>path:last-child]:text-textInverse" /> : <Circle size={21} className="text-textMuted" />}
                    </span>
                    <span className="min-w-0">
                      <span className="block font-semibold text-text">{voice.label}</span>
                      <span className="mt-1 block text-sm text-textMuted">{voice.description}</span>
                    </span>
                  </button>
                  <button type="button" onClick={() => preview(voice)} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-border bg-surface text-primary transition hover:border-primary hover:bg-primary/10" aria-label={`${playing ? "Stop" : "Play"} ${voice.label} voice preview`}>
                    {playing ? <Square size={17} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        <div className="mt-6 rounded-3xl border border-border bg-surface p-4 shadow-sm sm:p-6">
          <div className="mb-5 flex items-start justify-between">
            <div>
              <h3 className="text-lg font-semibold text-text">Billing & Plan</h3>
              <p className="mt-1 text-sm text-textMuted">View your current subscription and upgrade your chambers.</p>
            </div>
          </div>

          <BillingSection />
        </div>
      </section>

      <section className="mx-auto w-full max-w-4xl py-2 sm:py-6">
        <div className="rounded-3xl border border-border bg-surface p-4 shadow-sm sm:p-6">
          <h3 className="text-lg font-semibold text-text">Profile</h3>
          <ProfileEditor />
        </div>
      </section>
    </MainLayout>
  );
}
          <ProfileEditor />

function BillingSection() {
  const { plan, fetchPlan, startCheckout, loading } = useBilling();
  const openUpgradeModal = useUI((s) => s.openUpgradeModal);

  useEffect(() => { fetchPlan().catch(() => {}); }, []);

  const handleUpgrade = async () => {
    try {
      const res = await startCheckout({ tier: 'STARTER' });
      if (res.provider === 'paystack' && res.authorization_url) {
        window.location.href = res.authorization_url;
      } else {
        // mock provider
        openUpgradeModal({ message: 'Dev checkout created (mock). Complete via webhook to finalize upgrade.', upgrade_required: null });
      }
    } catch (err) {
      if (err.tierGate) {
        openUpgradeModal(err.tierGate);
      } else {
        openUpgradeModal({ message: err.message || 'Checkout failed', upgrade_required: null });
      }
    }
  };

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="rounded-lg border border-border bg-background p-4">
        <div className="text-sm text-textMuted">Current tier</div>
        <div className="mt-2 flex items-center justify-between">
          <div>
            <div className="text-lg font-semibold text-text">{plan?.tier || 'FREE'}</div>
            <div className="text-sm text-textMuted">Members: {plan?.chambers_id ? 'Chambers' : 'Personal'}</div>
          </div>
          <div>
            <button disabled={loading} onClick={handleUpgrade} className="rounded-md bg-primary px-4 py-2 text-text-inverse">Upgrade</button>
          </div>
        </div>
      </div>
      <div className="rounded-lg border border-border bg-background p-4">
        <div className="text-sm text-textMuted">Usage</div>
        <div className="mt-2 text-sm text-textMuted">{plan ? JSON.stringify(plan.usage || {}) : 'No usage data'}</div>
      </div>
    </div>
  );
}
function ProfileEditor() {
  const { profile, fetchProfile, updateProfile, loading } = useProfile();
  const [role, setRole] = useState(profile?.role || "ASSOCIATE");

  useEffect(() => { fetchProfile().then(p => setRole(p?.role || 'ASSOCIATE')).catch(() => {}); }, []);

  const roles = [
    { value: 'PRINCIPAL', label: 'Principal' },
    { value: 'PARTNER', label: 'Partner' },
    { value: 'ASSOCIATE', label: 'Associate' },
    { value: 'TRAINEE', label: 'Trainee' },
    { value: 'LAW_STUDENT', label: 'Law Student' },
    { value: 'SAN', label: 'SAN' },
  ];

  const save = async () => {
    try {
      await updateProfile({ role });
      alert('Profile updated');
    } catch (err) {
      alert('Failed to update profile: ' + (err.message || String(err)));
    }
  };

  return (
    <div className="mt-4 grid gap-4 sm:grid-cols-3">
      <div className="sm:col-span-2">
        <label className="block text-sm text-textMuted">Role</label>
        <div className="mt-2">
          <Select value={role} onChange={setRole} options={roles} placeholder="Select role" />
        </div>
      </div>
      <div className="flex items-end">
        <button onClick={save} disabled={loading} className="rounded-md bg-primary px-4 py-2 text-text-inverse">Save</button>
      </div>
    </div>
  );
}

export default Settings;
