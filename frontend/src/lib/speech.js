export const SPEECH_PREVIEW = "Hello. This is how I will read your chats and responses.";

export function prepareTextForSpeech(value = "") {
  return value
    .replace(/```[\s\S]*?```/g, " Code example omitted. ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/^\s*\d+[.)]\s+/gm, "")
    .replace(/[>*_~|]/g, " ")
    .replace(/([,;:])\s*/g, "$1 ")
    .replace(/\s+/g, " ")
    .trim();
}

export function resolveVoice(voices, preference) {
  if (!voices?.length) return null;

  const english = voices.filter((voice) => voice.lang?.toLowerCase().startsWith("en"));
  const candidates = english.length ? english : voices;
  const indexByPreference = { default: 0, calm: 1, bright: 2, deep: 3, clear: 4, quick: 5 };
  return candidates[indexByPreference[preference] % candidates.length] || candidates[0];
}

export function speakText(text, preference, profile, onEnd) {
  if (!("speechSynthesis" in window)) return null;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(prepareTextForSpeech(text));
  const voice = resolveVoice(window.speechSynthesis.getVoices(), preference);
  if (voice) utterance.voice = voice;
  utterance.lang = voice?.lang || "en-US";
  utterance.pitch = profile?.pitch || 1;
  utterance.rate = profile?.rate || 1;
  utterance.onend = () => onEnd?.();
  utterance.onerror = () => onEnd?.();
  window.speechSynthesis.speak(utterance);
  return utterance;
}
