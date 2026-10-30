"use client";

import { Check, Mic, MicOff, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cx } from "@/lib/format";

interface VoiceFieldProps {
  id?: string;
  label?: string;
  required?: boolean;
  tooltip?: string;
  value: string;
  onChange: (val: string) => void;
  placeholder?: string;
  type?: "text" | "textarea" | "number";
  rows?: number;
  maxChars?: number;
  onRegenerate?: () => void;
  regenerating?: boolean;
  filledByKaru?: boolean;
  filledByMeesho?: boolean;
  lowConfidence?: boolean;
  className?: string;
  error?: string;
}

export function VoiceField({
  id,
  label,
  required,
  tooltip,
  value,
  onChange,
  placeholder,
  type = "text",
  rows = 3,
  maxChars,
  onRegenerate,
  regenerating,
  filledByKaru,
  filledByMeesho,
  lowConfidence,
  className,
  error,
}: VoiceFieldProps) {
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    // Check Web Speech API support
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-IN";

      recognition.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((r: any) => r[0].transcript)
          .join("");
        if (transcript) {
          onChange(value ? `${value} ${transcript}` : transcript);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.onerror = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {}
      }
    };
  }, [value, onChange]);

  const toggleMic = () => {
    if (!recognitionRef.current) {
      // Fallback simulation
      if (!isListening) {
        setIsListening(true);
        setTimeout(() => {
          setIsListening(false);
          onChange(
            value
              ? `${value} pure handwoven silk with natural zari border`
              : "Pure handwoven silk with natural zari border"
          );
        }, 2500);
      } else {
        setIsListening(false);
      }
      return;
    }

    if (isListening) {
      try {
        recognitionRef.current.stop();
      } catch {}
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch {
        setIsListening(false);
      }
    }
  };

  return (
    <div className={cx("flex flex-col gap-1 w-full", className)}>
      {label && (
        <div className="flex items-center justify-between">
          <label htmlFor={id} className="text-[13px] font-medium text-[#111827] flex items-center gap-1">
            <span>{label}</span>
            {required && <span className="text-red-500 font-bold">*</span>}
            {tooltip && (
              <span className="text-[#A3A7B5] cursor-help text-[11px]" title={tooltip}>
                ⓘ
              </span>
            )}
          </label>
          {(filledByMeesho || filledByKaru) && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[#4B3BD1] bg-[#EFEDFC] px-1.5 py-0.5 rounded">
              ✨ Filled by Meesho
            </span>
          )}
        </div>
      )}

      <div className="relative w-full">
        {type === "textarea" ? (
          <textarea
            id={id}
            rows={rows}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            maxLength={maxChars}
            className={cx(
              "w-full rounded-md border bg-white p-3 pe-16 text-[13.5px] text-[#111827] placeholder:text-[#A3A7B5] focus:outline-none transition-colors resize-y",
              error
                ? "border-red-500 focus:border-red-600 focus:ring-1 focus:ring-red-500"
                : lowConfidence
                ? "border-amber-400 bg-amber-50/20 focus:border-[#4B3BD1]"
                : "border-[#E3E5EC] focus:border-[#4B3BD1] focus:ring-1 focus:ring-[#4B3BD1]"
            )}
          />
        ) : (
          <input
            id={id}
            type={type}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            maxLength={maxChars}
            className={cx(
              "w-full h-9 rounded-md border bg-white px-3 pe-16 text-[13.5px] text-[#111827] placeholder:text-[#A3A7B5] focus:outline-none transition-colors",
              error
                ? "border-red-500 focus:border-red-600 focus:ring-1 focus:ring-red-500"
                : lowConfidence
                ? "border-amber-400 bg-amber-50/20 focus:border-[#4B3BD1]"
                : "border-[#E3E5EC] focus:border-[#4B3BD1] focus:ring-1 focus:ring-[#4B3BD1]"
            )}
          />
        )}

        {/* Embedded Action Icons inside field (Mic + Regenerate) */}
        <div
          className={cx(
            "absolute end-2 flex items-center gap-1",
            type === "textarea" ? "top-2.5" : "top-1/2 -translate-y-1/2"
          )}
        >
          {onRegenerate && (
            <button
              type="button"
              onClick={onRegenerate}
              disabled={regenerating}
              title="Regenerate field using AI"
              className="p-1 rounded text-[#6B7080] hover:text-[#4B3BD1] hover:bg-[#F1F2F6] disabled:opacity-50"
            >
              <RefreshCw className={cx("size-3.5", regenerating && "animate-spin text-[#4B3BD1]")} />
            </button>
          )}

          <button
            type="button"
            onClick={toggleMic}
            title={isListening ? "Listening... click to stop" : "Speak to fill field"}
            className={cx(
              "p-1 rounded-full transition-all flex items-center justify-center",
              isListening
                ? "bg-red-500 text-white animate-pulse shadow-xs"
                : "text-[#4B3BD1] hover:bg-[#EFEDFC]"
            )}
          >
            {isListening ? <Mic className="size-4" /> : <Mic className="size-4" />}
          </button>
        </div>
      </div>

      {/* Helper / Error / Counter footer */}
      <div className="flex items-center justify-between text-[11px] text-[#6B7080] px-0.5">
        {error ? (
          <span className="text-red-600 font-medium">{error}</span>
        ) : lowConfidence ? (
          <span className="text-amber-700">Please review this AI-extracted field</span>
        ) : (
          <span />
        )}

        {maxChars && (
          <span className="ms-auto text-[#A3A7B5]">
            {value.length}/{maxChars}
          </span>
        )}
      </div>
    </div>
  );
}
