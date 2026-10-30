"use client";

import { Bookmark, ChevronRight, HelpCircle, Image as ImageIcon, Info, Mic, Play, RotateCcw, Search, Sparkles, UploadCloud, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { cx } from "@/lib/format";

export interface CategoryNode {
  id: string;
  name: string;
  isLeaf?: boolean;
  children?: CategoryNode[];
  sampleImage?: string;
}

interface CategoryColumnsProps {
  categories: CategoryNode[];
  recentCategories?: { id: string; path: string[] }[];
  onSelectLeaf: (path: CategoryNode[], categoryId: string) => void;
  onPhotosSelected: (files: File[]) => void;
  onVoiceRecorded?: (audioBlob: Blob, transcript: string, durationS: number) => void;
  onContinue: () => void;
  uploadedPhotosCount: number;
}

export function CategoryColumns({
  categories,
  recentCategories = [
    { id: "saree-bhagalpuri", path: ["Clothing & Textiles", "Sarees", "Silk Sarees", "Bhagalpuri"] },
    { id: "pottery-bowls", path: ["Home & Living", "Pottery", "Terracotta Bowls"] },
  ],
  onSelectLeaf,
  onPhotosSelected,
  onVoiceRecorded,
  onContinue,
  uploadedPhotosCount,
}: CategoryColumnsProps) {
  const [search, setSearch] = useState("");
  const [level1, setLevel1] = useState<string>("Clothing & Textiles");
  const [level2, setLevel2] = useState<string>("Sarees");
  const [level3, setLevel3] = useState<string>("Silk Sarees");
  const [level4, setLevel4] = useState<string>("Bhagalpuri");

  // Voice recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [recordedAudio, setRecordedAudio] = useState<string | null>(null);
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const timerRef = useRef<any>(null);

  // Derive columns data
  const col1Items = categories;
  const col2Items = useMemo(
    () => col1Items.find((c) => c.name === level1)?.children || [],
    [col1Items, level1]
  );
  const col3Items = useMemo(
    () => col2Items.find((c) => c.name === level2)?.children || [],
    [col2Items, level2]
  );
  const col4Items = useMemo(
    () => col3Items.find((c) => c.name === level3)?.children || [],
    [col3Items, level3]
  );

  const selectedPathNodes = useMemo(() => {
    const p1 = col1Items.find((c) => c.name === level1);
    const p2 = col2Items.find((c) => c.name === level2);
    const p3 = col3Items.find((c) => c.name === level3);
    const p4 = col4Items.find((c) => c.name === level4);
    return [p1, p2, p3, p4].filter(Boolean) as CategoryNode[];
  }, [col1Items, col2Items, col3Items, col4Items, level1, level2, level3, level4]);

  const activeLeafId = selectedPathNodes[selectedPathNodes.length - 1]?.id || "saree-bhagalpuri";

  useEffect(() => {
    onSelectLeaf(selectedPathNodes, activeLeafId);
  }, [selectedPathNodes, activeLeafId, onSelectLeaf]);

  // Voice recording timer
  useEffect(() => {
    if (isRecording) {
      setRecordSeconds(0);
      timerRef.current = setInterval(() => {
        setRecordSeconds((s) => {
          if (s >= 120) {
            handleStopRecording();
            return 120;
          }
          return s + 1;
        });
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isRecording]);

  const handleStartRecording = () => {
    setIsRecording(true);
    setRecordedAudio(null);
    setVoiceTranscript("");
  };

  const handleStopRecording = () => {
    setIsRecording(false);
    const mockTranscript =
      "Pure Bhagalpuri handwoven tussar silk saree with natural madder dye and zari border, length 5.5 meters with blouse piece. Took 12 days to weave on traditional pit loom. Expected price 2,800 rupees.";
    setVoiceTranscript(mockTranscript);
    setRecordedAudio("mock-audio-url");

    // Call callback with dummy blob
    const dummyBlob = new Blob(["mock-audio"], { type: "audio/webm" });
    onVoiceRecorded?.(dummyBlob, mockTranscript, recordSeconds || 12);
  };

  const handleImagePicker = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onPhotosSelected(Array.from(e.target.files));
    }
  };

  return (
    <div className="flex flex-col gap-5">
      {/* Search Category Box */}
      <div className="relative w-full max-w-xl">
        <Search className="pointer-events-none absolute start-3.5 top-1/2 -translate-y-1/2 size-4 text-[#A3A7B5]" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search category (e.g. Handloom saree in Clothing & Textiles)"
          className="w-full h-10 ps-10 pe-4 rounded-md border border-[#E3E5EC] bg-white text-[13.5px] text-[#111827] placeholder:text-[#A3A7B5] focus:outline-none focus:border-[#4B3BD1] focus:ring-1 focus:ring-[#4B3BD1] shadow-2xs"
        />
        {search && (
          <button
            type="button"
            onClick={() => setSearch("")}
            className="absolute end-3 top-1/2 -translate-y-1/2 text-[#A3A7B5] hover:text-[#111827]"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      {/* Main Cascading Section + Right Panel */}
      <div className="flex flex-col lg:flex-row items-start gap-5">
        {/* Cascading Columns (Horizontally scrollable on small screens) */}
        <div className="flex-1 w-full overflow-x-auto pb-2">
          <div className="inline-flex rounded-lg border border-[#E3E5EC] bg-white shadow-xs divide-x divide-[#E3E5EC] min-w-full lg:min-w-0">
            {/* Column 1: Your Categories + Level 1 */}
            <div className="w-[200px] shrink-0 h-[340px] overflow-y-auto flex flex-col text-[13px] py-1">
              <div className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-[#7C8196] flex items-center gap-1.5">
                <Bookmark className="size-3 text-[#4B3BD1]" />
                <span>Your Categories</span>
              </div>
              {recentCategories.map((rc) => (
                <button
                  key={rc.id}
                  type="button"
                  onClick={() => {
                    if (rc.path[0]) setLevel1(rc.path[0]);
                    if (rc.path[1]) setLevel2(rc.path[1]);
                    if (rc.path[2]) setLevel3(rc.path[2]);
                    if (rc.path[3]) setLevel4(rc.path[3]);
                  }}
                  className="px-3 py-2 text-start font-medium text-[#4B3BD1] hover:bg-[#EFEDFC] flex items-center justify-between"
                >
                  <span className="truncate">{rc.path[rc.path.length - 1]}</span>
                  <ChevronRight className="size-3 text-[#7C8196]" />
                </button>
              ))}

              <div className="my-1 border-t border-[#E3E5EC]" />
              <div className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-[#7C8196]">
                All Categories
              </div>

              {col1Items.map((c) => {
                const isSelected = c.name === level1;
                return (
                  <button
                    key={c.name}
                    type="button"
                    onClick={() => {
                      setLevel1(c.name);
                      const nextL2 = c.children?.[0]?.name || "";
                      setLevel2(nextL2);
                      const nextL3 = c.children?.[0]?.children?.[0]?.name || "";
                      setLevel3(nextL3);
                      const nextL4 = c.children?.[0]?.children?.[0]?.children?.[0]?.name || "";
                      setLevel4(nextL4);
                    }}
                    className={cx(
                      "px-3 py-2.5 text-start font-medium flex items-center justify-between transition-colors",
                      isSelected
                        ? "bg-[#4B3BD1] text-white font-semibold"
                        : "text-[#111827] hover:bg-[#F1F2F6]"
                    )}
                  >
                    <span className="truncate">{c.name}</span>
                    <ChevronRight className={cx("size-3.5", isSelected ? "text-white" : "text-[#7C8196]")} />
                  </button>
                );
              })}
            </div>

            {/* Column 2: Level 2 */}
            <div className="w-[200px] shrink-0 h-[340px] overflow-y-auto flex flex-col text-[13px] py-1">
              {col2Items.map((c) => {
                const isSelected = c.name === level2;
                return (
                  <button
                    key={c.name}
                    type="button"
                    onClick={() => {
                      setLevel2(c.name);
                      const nextL3 = c.children?.[0]?.name || "";
                      setLevel3(nextL3);
                      const nextL4 = c.children?.[0]?.children?.[0]?.name || "";
                      setLevel4(nextL4);
                    }}
                    className={cx(
                      "px-3 py-2.5 text-start font-medium flex items-center justify-between transition-colors",
                      isSelected
                        ? "bg-[#4B3BD1] text-white font-semibold"
                        : "text-[#111827] hover:bg-[#F1F2F6]"
                    )}
                  >
                    <span className="truncate">{c.name}</span>
                    <ChevronRight className={cx("size-3.5", isSelected ? "text-white" : "text-[#7C8196]")} />
                  </button>
                );
              })}
            </div>

            {/* Column 3: Level 3 */}
            <div className="w-[200px] shrink-0 h-[340px] overflow-y-auto flex flex-col text-[13px] py-1">
              {col3Items.map((c) => {
                const isSelected = c.name === level3;
                return (
                  <button
                    key={c.name}
                    type="button"
                    onClick={() => {
                      setLevel3(c.name);
                      const nextL4 = c.children?.[0]?.name || "";
                      setLevel4(nextL4);
                    }}
                    className={cx(
                      "px-3 py-2.5 text-start font-medium flex items-center justify-between transition-colors",
                      isSelected
                        ? "bg-[#4B3BD1] text-white font-semibold"
                        : "text-[#111827] hover:bg-[#F1F2F6]"
                    )}
                  >
                    <span className="truncate">{c.name}</span>
                    <ChevronRight className={cx("size-3.5", isSelected ? "text-white" : "text-[#7C8196]")} />
                  </button>
                );
              })}
            </div>

            {/* Column 4: Level 4 */}
            <div className="w-[200px] shrink-0 h-[340px] overflow-y-auto flex flex-col text-[13px] py-1">
              {col4Items.map((c) => {
                const isSelected = c.name === level4;
                return (
                  <button
                    key={c.name}
                    type="button"
                    onClick={() => setLevel4(c.name)}
                    className={cx(
                      "px-3 py-2.5 text-start font-medium flex items-center justify-between transition-colors",
                      isSelected
                        ? "bg-[#4B3BD1] text-white font-semibold"
                        : "text-[#111827] hover:bg-[#F1F2F6]"
                    )}
                  >
                    <span className="truncate">{c.name}</span>
                    {isSelected && <span className="size-1.5 rounded-full bg-white ms-1" />}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Panel (Sticky 340px) */}
        <div className="w-full lg:w-[340px] shrink-0 flex flex-col gap-4">
          {/* Breadcrumb Header Card */}
          <div className="p-4 rounded-lg border border-[#E3E5EC] bg-white shadow-xs">
            <p className="text-[11.5px] font-semibold text-[#6B7080] uppercase tracking-wider mb-1">
              Selected Category
            </p>
            <p className="text-[13.5px] font-semibold text-[#111827] leading-tight">
              {[level1, level2, level3, level4].filter(Boolean).join(" › ")}
            </p>

            {/* Sample Image */}
            <div className="mt-3 relative h-36 rounded-md overflow-hidden bg-[#F1F2F6] border border-[#E3E5EC] flex items-center justify-center">
              <img
                src="https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=600&q=80"
                alt="Sample saree category"
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-x-0 bottom-0 bg-black/60 p-2 text-center text-white text-[11px]">
                Please provide only front image for each product
              </div>
            </div>

            {/* Upload Button */}
            <div className="mt-3">
              <label className="cursor-pointer flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-md bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white text-[13px] font-semibold transition-colors shadow-xs">
                <UploadCloud className="size-4" />
                <span>+ Add Product Images</span>
                <input
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={handleImagePicker}
                  className="hidden"
                />
              </label>
              {uploadedPhotosCount > 0 && (
                <p className="text-[11.5px] font-medium text-[#16A34A] text-center mt-1.5">
                  ✓ {uploadedPhotosCount} photo{uploadedPhotosCount > 1 ? "s" : ""} selected
                </p>
              )}
            </div>
          </div>

          {/* Prominent Voice Description Card (Karu Snap+Speak Engine) */}
          <div className="p-4 rounded-lg border border-[#EFEDFC] bg-[#F8F7FD] shadow-xs flex flex-col gap-3">
            <div className="flex items-center gap-2 text-[#4B3BD1]">
              <Sparkles className="size-4" />
              <h4 className="text-[14px] font-semibold">Speak & Describe (AI Fill)</h4>
            </div>

            <p className="text-[12px] text-[#5C554D] leading-relaxed">
              Describe what it is, its weave, size, colour and price in your dialect. Meesho will fill the entire form automatically!
            </p>

            <div className="flex flex-col items-center justify-center py-2">
              <button
                type="button"
                onClick={isRecording ? handleStopRecording : handleStartRecording}
                className={cx(
                  "size-16 rounded-full flex items-center justify-center transition-all shadow-md active:scale-95",
                  isRecording
                    ? "bg-red-500 text-white animate-pulse ring-4 ring-red-200"
                    : "bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white ring-4 ring-[#EFEDFC]"
                )}
                title="Tap to speak"
              >
                <Mic className="size-7" />
              </button>

              <span className="text-[12px] font-semibold mt-2 text-[#111827]">
                {isRecording ? `Listening... ${recordSeconds}s / 120s` : "Tap to record voice"}
              </span>
            </div>

            {voiceTranscript && (
              <div className="p-2.5 rounded bg-white border border-[#E3E5EC] text-[12px] text-[#111827] leading-normal">
                <span className="font-semibold text-[#4B3BD1]">Captured: </span>
                <span>{voiceTranscript}</span>
              </div>
            )}
          </div>

          {/* Yellow Guidelines Box */}
          <div className="p-4 rounded-lg border border-[#F3DFA0] bg-[#FFF7DD] text-[#744210] text-[12px] flex flex-col gap-2.5">
            <div className="flex items-center gap-1.5 font-semibold text-[13px]">
              <Info className="size-4 text-[#D97706]" />
              <span>General Guidelines</span>
            </div>
            <ul className="list-disc list-inside space-y-1 text-[11.5px] leading-relaxed text-[#5C554D]">
              <li>One clear front photo is enough. Meesho generates the other variants automatically.</li>
              <li>Ensure daylight and plain neutral background for best AI verification.</li>
              <li>No watermarks or contact numbers on the photo.</li>
            </ul>
          </div>

          {/* Continue button */}
          <button
            type="button"
            onClick={onContinue}
            className="w-full py-2.5 px-4 rounded-md bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white text-[13.5px] font-semibold transition-colors shadow-xs flex items-center justify-center gap-1.5"
          >
            <span>Continue to Product Details</span>
            <ChevronRight className="size-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
