import { useEffect, useRef, useState } from "react";
import { useChat } from "../store/chat";

export default function useSpeechRecognition() {
    const setInput = useChat((s) => s.setInput);

    const recognitionRef = useRef(null);

    const [listening, setListening] =
        useState(false);

    useEffect(() => {
        const SpeechRecognition =
            window.SpeechRecognition ||
            window.webkitSpeechRecognition;

        if (!SpeechRecognition) return;

        const recognition =
            new SpeechRecognition();

        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = "en-US";

        recognition.onstart = () =>
            setListening(true);

        recognition.onend = () =>
            setListening(false);

        recognition.onresult = (event) => {
            let transcript = "";

            for (
                let i = event.resultIndex;
                i < event.results.length;
                i++
            ) {
                transcript +=
                    event.results[i][0].transcript;
            }

            setInput(transcript);
        };

        recognitionRef.current = recognition;
    }, [setInput]);

    const start = () =>
        recognitionRef.current?.start();

    const stop = () =>
        recognitionRef.current?.stop();

    return {
        listening,
        start,
        stop,
        supported:
            !!(
                window.SpeechRecognition ||
                window.webkitSpeechRecognition
            ),
    };
}