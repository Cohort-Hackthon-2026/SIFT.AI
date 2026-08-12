import { useEffect, useState } from "react";
import { Circle, CircleCheck, Play, Settings2, Square } from "lucide-react";

import MainLayout from "../components/layout/MainLayout";
import { useSettings } from "../../store/settings";
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
      </section>
    </MainLayout>
  );
}

export default Settings;
