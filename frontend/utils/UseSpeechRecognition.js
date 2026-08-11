import { useEffect, useRef, useState } from "react";
import { api } from "../src/lib/api";

export default function useSpeechRecognition() {
    const recognitionRef = useRef(null);
    const recorderRef = useRef(null);
    const streamRef = useRef(null);
    const chunksRef = useRef([]);
    const [status, setStatus] = useState("idle");
    const [transcript, setTranscript] = useState("");
    const [error, setError] = useState("");
    const hasNativeRecognition = typeof window !== "undefined" && !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    const hasRecorder = typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined";

    useEffect(() => {
        const SpeechRecognition =
            window.SpeechRecognition ||
            window.webkitSpeechRecognition;

        if (!SpeechRecognition) return undefined;

        const recognition =
            new SpeechRecognition();

        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "en-US";

        recognition.onstart = () => setStatus("listening");

        recognition.onend = () => setStatus((current) => current === "error" ? current : "idle");
        recognition.onerror = (event) => {
            setError(event.error === "not-allowed" ? "Microphone permission was denied." : "Speech recognition could not continue.");
            setStatus("error");
        };

        recognition.onresult = (event) => {
            let transcript = "";

            for (
                let i = 0;
                i < event.results.length;
                i++
            ) {
                transcript +=
                    event.results[i][0].transcript;
            }

            setTranscript(transcript);
            window.dispatchEvent(new CustomEvent("voice-transcript", { detail: { text: transcript, replaceInterim: true } }));
        };

        recognitionRef.current = recognition;
        return () => recognition.abort();
    }, []);

    const start = async () => {
        setError("");
        setTranscript("");

        if (recognitionRef.current) {
            try {
                recognitionRef.current.start();
            } catch {
                // Ignore repeated starts while the recognition service is active.
            }
            return;
        }

        try {
            const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = mediaStream;
            chunksRef.current = [];
            const recorder = new MediaRecorder(mediaStream);
            recorderRef.current = recorder;
            recorder.ondataavailable = (event) => {
                if (event.data.size) chunksRef.current.push(event.data);
            };
            recorder.onstop = async () => {
                setStatus("transcribing");
                mediaStream.getTracks().forEach((track) => track.stop());
                try {
                    const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
                    const formData = new FormData();
                    formData.append("file", blob, "voice-input.webm");
                    const result = await api.transcribeAudio(formData, "en");
                    const text = result?.text?.trim() || "";
                    setTranscript(text);
                    window.dispatchEvent(new CustomEvent("voice-transcript", { detail: { text } }));
                    setStatus("idle");
                } catch (err) {
                    setError(err.message || "The recording could not be transcribed.");
                    setStatus("error");
                }
            };
            recorder.start();
            setStatus("listening");
        } catch (err) {
            setError(err.name === "NotAllowedError" ? "Microphone permission was denied." : "The microphone could not be started.");
            setStatus("error");
        }
    };

    const stop = () => {
        if (recognitionRef.current && status === "listening") {
            recognitionRef.current.stop();
        } else if (recorderRef.current?.state === "recording") {
            recorderRef.current.stop();
        }
    };

    const reset = () => {
        recognitionRef.current?.abort();
        if (recorderRef.current?.state === "recording") recorderRef.current.stop();
        streamRef.current?.getTracks().forEach((track) => track.stop());
        setStatus("idle");
        setError("");
    };

    return {
        status,
        listening: status === "listening",
        transcript,
        error,
        start,
        stop,
        reset,
        supported: hasNativeRecognition || hasRecorder,
    };
}
