"use client";

import { AlertTriangle, Loader2 } from "lucide-react";
import { useState } from "react";
import { cx } from "@/lib/format";

interface StickyFooterProps {
  onDiscard: () => void;
  onSaveBack?: () => void;
  onSubmit: () => void;
  discardText?: string;
  saveBackText?: string;
  submitText?: string;
  isSaving?: boolean;
  isSubmitting?: boolean;
  disabled?: boolean;
  className?: string;
}

export function StickyFooter({
  onDiscard,
  onSaveBack,
  onSubmit,
  discardText = "Discard",
  saveBackText = "Save and go back",
  submitText = "Submit",
  isSaving = false,
  isSubmitting = false,
  disabled = false,
  className,
}: StickyFooterProps) {
  const [showDiscardConfirm, setShowDiscardConfirm] = useState(false);

  return (
    <>
      <footer
        className={cx(
          "sticky bottom-0 inset-x-0 h-16 bg-white border-t border-[#E3E5EC] px-4 sm:px-8 flex items-center justify-between z-30 shadow-[0_-4px_12px_rgba(20,24,40,0.05)]",
          className
        )}
      >
        {/* Left Discard Button */}
        <div>
          <button
            type="button"
            onClick={() => setShowDiscardConfirm(true)}
            disabled={isSubmitting || isSaving}
            className="px-4 py-2 rounded-md border border-[#E3E5EC] bg-white hover:bg-red-50 hover:border-red-200 text-[#6B7080] hover:text-red-600 text-[13px] font-semibold transition-colors"
          >
            {discardText}
          </button>
        </div>

        {/* Right Action Buttons */}
        <div className="flex items-center gap-3">
          {onSaveBack && (
            <button
              type="button"
              onClick={onSaveBack}
              disabled={disabled || isSubmitting || isSaving}
              className="px-4 py-2 rounded-md border border-[#E3E5EC] bg-white hover:bg-[#F1F2F6] text-[#111827] text-[13px] font-semibold transition-colors disabled:opacity-50"
            >
              {isSaving ? "Saving..." : saveBackText}
            </button>
          )}

          <button
            type="button"
            onClick={onSubmit}
            disabled={disabled || isSubmitting || isSaving}
            className="px-6 py-2 rounded-md bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white text-[13px] font-semibold transition-colors shadow-xs disabled:opacity-50 flex items-center gap-1.5"
          >
            {isSubmitting && <Loader2 className="size-4 animate-spin" />}
            <span>{submitText}</span>
          </button>
        </div>
      </footer>

      {/* Discard confirmation modal */}
      {showDiscardConfirm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="bg-white rounded-xl shadow-2xl max-w-sm w-full p-5 flex flex-col gap-3 animate-in fade-in duration-150">
            <div className="flex items-center gap-2.5 text-red-600 font-semibold text-[15px]">
              <AlertTriangle className="size-5" />
              <span>Discard this draft?</span>
            </div>
            <p className="text-[13px] text-[#5C554D] leading-normal">
              Any unsaved product details and uploaded photos will be discarded. Are you sure you want to leave?
            </p>
            <div className="flex items-center justify-end gap-2.5 mt-2">
              <button
                type="button"
                onClick={() => setShowDiscardConfirm(false)}
                className="px-3.5 py-1.5 rounded-md border border-[#E3E5EC] text-[13px] font-medium text-[#111827] hover:bg-[#F1F2F6]"
              >
                Keep editing
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowDiscardConfirm(false);
                  onDiscard();
                }}
                className="px-3.5 py-1.5 rounded-md bg-red-600 hover:bg-red-700 text-white text-[13px] font-semibold"
              >
                Yes, discard
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
