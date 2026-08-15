import { useEffect, useState } from "react";
import {
  Circle,
  CircleCheck,
  Play,
  Settings2,
  Square,
  Zap,
  MessageSquare,
  FileText,
  Download,
  Mic,
  Calendar,
  Sparkles,
  Shield,
  CreditCard,
  Building2,
  Globe,
  ShieldCheck,
  ArrowUpRight,
  Info,
} from "lucide-react";
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
      <section className="mx-auto w-full max-w-4xl py-2 sm:py-6 space-y-6">
        {/* Page Header */}
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Settings2 size={24} />
          </div>
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-text sm:text-3xl">Settings & Preferences</h2>
            <p className="mt-1 max-w-2xl text-sm text-textMuted sm:text-base">
              Manage your legal practitioner profile, subscription quotas, and audio playback voice.
            </p>
          </div>
        </div>

        {/* 1. Billing & Usage Dashboard */}
        <div className="rounded-3xl border border-border bg-surface p-5 shadow-sm sm:p-7">
          <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/60 pb-5">
            <div>
              <div className="flex items-center gap-2">
                <CreditCard size={20} className="text-primary" />
                <h3 className="text-lg font-bold text-text">Subscription & Usage Quotas</h3>
              </div>
              <p className="mt-1 text-xs sm:text-sm text-textMuted">
                Real-time tracking of your monthly research queries, uploads, memo exports, and audio quotas.
              </p>
            </div>
          </div>

          <BillingSection />
        </div>

        {/* 2. Reading Voice Section */}
        <div className="rounded-3xl border border-border bg-surface p-5 shadow-sm sm:p-7">
          <div className="mb-5">
            <h3 className="text-lg font-bold text-text">Audio Reading Voice</h3>
            <p className="mt-1 text-xs sm:text-sm text-textMuted">Select a voice or play a preview for legal text-to-speech audio briefs.</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {voices.map((voice) => {
              const selected = selectedVoice === voice.value;
              const playing = previewing === voice.value;
              return (
                <div
                  key={voice.value}
                  className={`flex min-w-0 items-center gap-3 rounded-2xl border p-3 transition sm:p-4 ${
                    selected ? "border-primary bg-primary/10 shadow-sm" : "border-border bg-background/60 hover:border-primary/50"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => setVoice(voice.value)}
                    className="flex min-w-0 flex-1 items-start gap-3 text-left"
                    aria-pressed={selected}
                  >
                    <span className="mt-0.5 shrink-0 text-primary" aria-hidden="true">
                      {selected ? (
                        <CircleCheck size={21} fill="currentColor" className="text-primary [&>path:last-child]:text-textInverse" />
                      ) : (
                        <Circle size={21} className="text-textMuted" />
                      )}
                    </span>
                    <span className="min-w-0">
                      <span className="block font-semibold text-text">{voice.label}</span>
                      <span className="mt-1 block text-xs text-textMuted">{voice.description}</span>
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => preview(voice)}
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-border bg-surface text-primary transition hover:border-primary hover:bg-primary/10 active:scale-95"
                    aria-label={`${playing ? "Stop" : "Play"} ${voice.label} voice preview`}
                  >
                    {playing ? <Square size={16} fill="currentColor" /> : <Play size={16} fill="currentColor" />}
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* 3. Practitioner Profile Section */}
        <div className="rounded-3xl border border-border bg-surface p-5 shadow-sm sm:p-7">
          <div className="mb-5">
            <h3 className="text-lg font-bold text-text">Practitioner Profile</h3>
            <p className="mt-1 text-xs sm:text-sm text-textMuted">
              Customizes jurisdiction grounding, NWLR citations, and chambers exports.
            </p>
          </div>
          <ProfileEditor />
        </div>
      </section>
    </MainLayout>
  );
}

function BillingSection() {
  const { plan, fetchPlan } = useBilling();
  const openBillingModal = useUI((s) => s.openBillingModal);

  useEffect(() => {
    fetchPlan().catch(() => {});
  }, [fetchPlan]);

  const tier = plan?.tier || "FREE";
  const quotas = plan?.usage?.quotas || {};

  const rawRenewalDate =
    plan?.usage?.renewal_date ||
    plan?.usage?.period_end ||
    plan?.subscription?.period_end;

  const renewalDate = rawRenewalDate
    ? new Date(rawRenewalDate).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : (() => {
        const now = new Date();
        const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, now.getDate());
        return nextMonth.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        });
      })();

  const tierBadgeStyles = {
    FREE: "bg-slate-500/10 text-slate-600 dark:text-slate-300 border-slate-500/30",
    STARTER: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30",
    PRO: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30",
    CHAMBERS: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
  };

  const usageCards = [
    {
      key: "QUERY",
      label: "AI Research Queries",
      icon: MessageSquare,
      unit: "queries",
      color: "from-blue-500 to-indigo-600",
      barColor: "bg-blue-500",
      description: "Strict & Enhanced mode queries",
    },
    {
      key: "DOC_UPLOAD",
      label: "Document & Image Uploads",
      icon: FileText,
      unit: "files",
      color: "from-emerald-500 to-teal-600",
      barColor: "bg-emerald-500",
      description: "PDFs & OCR scanned evidence",
    },
    {
      key: "EXPORT",
      label: "Memo & Brief Exports",
      icon: Download,
      unit: "exports",
      color: "from-purple-500 to-pink-600",
      barColor: "bg-purple-500",
      description: "Chambers PDF/Word deliverables",
    },
    {
      key: "AUDIO_MIN",
      label: "Voice & Audio Minutes",
      icon: Mic,
      unit: "mins",
      color: "from-amber-500 to-orange-600",
      barColor: "bg-amber-500",
      description: "Speech transcription & audio briefs",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner: Tier & Action Card */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-background via-background to-primary/5 p-5 sm:p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-textMuted">Active Plan</span>
              <span
                className={`rounded-full border px-3 py-0.5 text-xs font-bold uppercase tracking-wider shadow-sm ${
                  tierBadgeStyles[tier] || tierBadgeStyles.FREE
                }`}
              >
                {tier} Plan
              </span>
              <span className="rounded-full bg-surface border border-border px-2.5 py-0.5 text-[11px] font-medium text-textMuted flex items-center gap-1">
                <Building2 size={12} className="text-primary" />
                {plan?.chambers_id ? "Chambers Seat" : "Individual Practitioner"}
              </span>
            </div>

            <p className="text-xs sm:text-sm text-textMuted flex items-center gap-1.5">
              <Calendar size={14} className="text-textMuted" />
              <span>
                {tier === "FREE"
                  ? `Monthly quotas reset on ${renewalDate}`
                  : `Next renewal date: ${renewalDate} · Monthly billing`}
              </span>
            </p>
          </div>


          <button
            type="button"
            onClick={openBillingModal}
            className="flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-textInverse shadow-lg shadow-primary/25 hover:bg-primary/90 active:scale-95 transition"
          >
            <Zap size={16} />
            <span>Upgrade Subscription</span>
            <ArrowUpRight size={15} />
          </button>
        </div>
      </div>

      {/* Usage Quota Breakdown Grid */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h4 className="text-xs font-bold uppercase tracking-wider text-textMuted">Monthly Usage Quotas</h4>
          <span className="text-[11px] text-textMuted flex items-center gap-1">
            <Info size={12} />
            Quotas reset at beginning of each monthly cycle
          </span>
        </div>

        <div className="grid gap-3.5 sm:grid-cols-2">
          {usageCards.map((card) => {
            const data = quotas[card.key] || { used: 0, limit: 1, remaining: 1 };
            const isUnlimited = data.limit === -1 || data.limit === 999999 || data.limit === null;
            const used = data.used || 0;
            const limit = isUnlimited ? "∞" : data.limit || 1;
            const remaining = isUnlimited ? "Unlimited" : data.remaining ?? (data.limit - used);
            const percentage = isUnlimited ? 0 : Math.min(100, Math.round((used / data.limit) * 100));

            // Determine bar warning color
            const barBg =
              percentage >= 90
                ? "bg-rose-500"
                : percentage >= 70
                ? "bg-amber-500"
                : card.barColor;

            const Icon = card.icon;

            return (
              <div
                key={card.key}
                className="group rounded-2xl border border-border bg-background/80 p-4 transition hover:border-primary/40 hover:bg-background shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-surface border border-border/80 text-primary group-hover:scale-105 transition">
                      <Icon size={18} />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-text">{card.label}</div>
                      <div className="text-[11px] text-textMuted">{card.description}</div>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-xs font-bold text-text font-mono">
                      {used} <span className="text-textMuted font-normal">/ {limit}</span>
                    </span>
                    <div className="text-[10px] font-medium text-textMuted">
                      {isUnlimited ? "Unlimited" : `${remaining} ${card.unit} left`}
                    </div>
                  </div>
                </div>

                {/* Visual Progress Bar */}
                {!isUnlimited ? (
                  <div className="mt-3 space-y-1">
                    <div className="h-2 w-full overflow-hidden rounded-full bg-surface border border-border/40">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ease-out ${barBg}`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] text-textMuted">
                      <span>{percentage}% consumed</span>
                      <span>{remaining} remaining</span>
                    </div>
                  </div>
                ) : (
                  <div className="mt-3 flex items-center gap-1.5 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                    <Sparkles size={13} />
                    <span>Unlimited usage on active plan</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ProfileEditor() {
  const { profile, fetchProfile, updateProfile, loading } = useProfile();
  const [role, setRole] = useState(profile?.role || "ASSOCIATE");
  const [nbaNumber, setNbaNumber] = useState(profile?.nba_number || "");
  const [defaultJurisdiction, setDefaultJurisdiction] = useState(profile?.default_jurisdiction || "NG");
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    fetchProfile()
      .then((p) => {
        if (p) {
          setRole(p.role || "ASSOCIATE");
          setNbaNumber(p.nba_number || "");
          setDefaultJurisdiction(p.default_jurisdiction || "NG");
        }
      })
      .catch(() => {});
  }, [fetchProfile]);

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
    try {
      await updateProfile({
        role,
        nba_number: nbaNumber.trim() || null,
        default_jurisdiction: defaultJurisdiction,
      });
      setSavedSuccess(true);
      window.addToast?.("Profile preferences updated successfully.", "success");
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      window.addToast?.("Failed to update profile: " + (err.message || String(err)), "error");
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-textMuted">
            Professional Role
          </label>
          <Select value={role} onChange={setRole} options={roles} placeholder="Select role" />
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-textMuted">
            Primary Jurisdiction
          </label>
          <Select
            value={defaultJurisdiction}
            onChange={setDefaultJurisdiction}
            options={jurisdictions}
            placeholder="Select jurisdiction"
          />
        </div>
      </div>

      <div>
        <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-textMuted">
          <ShieldCheck size={14} className="text-primary" />
          NBA Enrolment / Bar Roll Number <span className="text-[10px] lowercase font-normal">(optional)</span>
        </label>
        <input
          type="text"
          value={nbaNumber}
          onChange={(e) => setNbaNumber(e.target.value)}
          placeholder="e.g. SCN/012345 or NBA-LAG-2024"
          className="w-full rounded-xl border border-border bg-background p-2.5 text-sm text-text outline-none focus:border-primary transition"
        />
        <p className="mt-1 text-[11px] text-textMuted">
          Displayed on formal Chambers Legal Research Memos and Table of Authorities exports.
        </p>
      </div>

      <div className="flex items-center justify-between pt-2">
        {savedSuccess ? (
          <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
            <CircleCheck size={15} /> Preferences saved
          </span>
        ) : (
          <span />
        )}

        <button
          type="button"
          onClick={handleSave}
          disabled={loading}
          className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-textInverse shadow-md shadow-primary/20 hover:bg-primary/90 active:scale-95 transition disabled:opacity-50"
        >
          {loading ? "Saving..." : "Save Preferences"}
        </button>
      </div>
    </div>
  );
}

export default Settings;

