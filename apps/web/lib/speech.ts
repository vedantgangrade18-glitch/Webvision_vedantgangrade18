"use client";

/** Voice capture for artisans: MediaRecorder for the audio file + (when the browser has it) the
 *  Web Speech API for an on-device transcript. The server prefers its own STT provider; the
 *  browser transcript is the fallback when no STT key is configured. */

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;
interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((e: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
}

export function speechRecognitionSupported(): boolean {
  if (typeof window === "undefined") return false;
  const w = window as unknown as { SpeechRecognition?: SpeechRecognitionCtor; webkitSpeechRecognition?: SpeechRecognitionCtor };
  return !!(w.SpeechRecognition || w.webkitSpeechRecognition);
}

function recognitionCtor(): SpeechRecognitionCtor | null {
  const w = window as unknown as { SpeechRecognition?: SpeechRecognitionCtor; webkitSpeechRecognition?: SpeechRecognitionCtor };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export function pickAudioMime(): string {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
  for (const c of candidates) if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(c)) return c;
  return "";
}

export interface Recording {
  blob: Blob;
  durationS: number;
  transcript: string;
}

export class VoiceRecorder {
  private recorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private chunks: Blob[] = [];
  private recognition: SpeechRecognitionLike | null = null;
  private transcript = "";
  private interim = "";
  private startedAt = 0;
  private analyser: AnalyserNode | null = null;
  private audioCtx: AudioContext | null = null;

  constructor(private lang: string, private onTranscript?: (text: string) => void) {}

  async start(): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    const mime = pickAudioMime();
    this.recorder = new MediaRecorder(this.stream, mime ? { mimeType: mime } : undefined);
    this.chunks = [];
    this.recorder.ondataavailable = (e) => e.data.size && this.chunks.push(e.data);
    this.recorder.start(250);
    this.startedAt = Date.now();
    try {
      this.audioCtx = new AudioContext();
      const src = this.audioCtx.createMediaStreamSource(this.stream);
      this.analyser = this.audioCtx.createAnalyser();
      this.analyser.fftSize = 256;
      src.connect(this.analyser);
    } catch {
      this.analyser = null;
    }
    const Ctor = recognitionCtor();
    if (Ctor) {
      try {
        const rec = new Ctor();
        rec.lang = this.lang;
        rec.continuous = true;
        rec.interimResults = true;
        rec.onresult = (e) => {
          let interim = "";
          for (let i = e.resultIndex; i < e.results.length; i++) {
            const r = e.results[i];
            if (r.isFinal) this.transcript += (this.transcript ? " " : "") + r[0].transcript.trim();
            else interim += r[0].transcript;
          }
          this.interim = interim;
          this.onTranscript?.(`${this.transcript} ${interim}`.trim());
        };
        rec.onerror = () => undefined;
        rec.start();
        this.recognition = rec;
      } catch {
        this.recognition = null;
      }
    }
  }

  /** 0–1 input level for the live waveform. */
  level(): number {
    if (!this.analyser) return 0;
    const data = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteTimeDomainData(data);
    let peak = 0;
    for (const v of data) peak = Math.max(peak, Math.abs(v - 128));
    return Math.min(1, peak / 64);
  }

  elapsed(): number {
    return this.startedAt ? (Date.now() - this.startedAt) / 1000 : 0;
  }

  async stop(): Promise<Recording> {
    const recorder = this.recorder;
    const durationS = this.elapsed();
    const blob = await new Promise<Blob>((resolve) => {
      if (!recorder || recorder.state === "inactive") return resolve(new Blob(this.chunks));
      recorder.onstop = () => resolve(new Blob(this.chunks, { type: recorder.mimeType || "audio/webm" }));
      recorder.stop();
    });
    try {
      this.recognition?.stop();
    } catch {
      /* already stopped */
    }
    this.stream?.getTracks().forEach((t) => t.stop());
    await this.audioCtx?.close().catch(() => undefined);
    const transcript = `${this.transcript} ${this.interim}`.trim();
    return { blob, durationS, transcript };
  }

  cancel(): void {
    try {
      this.recognition?.abort();
      this.recorder?.stop();
    } catch {
      /* ignore */
    }
    this.stream?.getTracks().forEach((t) => t.stop());
    this.audioCtx?.close().catch(() => undefined);
  }
}

/** Read a screen instruction aloud (A17 "voice prompts"). */
export function speak(text: string, lang: string): void {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  u.rate = 0.95;
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang?.toLowerCase().startsWith(lang.slice(0, 2).toLowerCase()));
  if (voice) u.voice = voice;
  window.speechSynthesis.speak(u);
}
