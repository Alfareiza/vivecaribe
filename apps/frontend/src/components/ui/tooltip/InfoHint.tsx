"use client";

import React from "react";

type InfoHintProps = {
  text: string;
  className?: string;
  /**
   * "center" (default) works for most fields. Use "right" only when the
   * icon sits near the modal/container's right edge, where a centered
   * popup would spill past it — right-anchoring flips the risk to the
   * left side, so don't default to it everywhere.
   */
  align?: "center" | "right";
};

const ALIGN_CLASSES: Record<NonNullable<InfoHintProps["align"]>, string> = {
  center: "left-1/2 -translate-x-1/2",
  right: "right-0",
};

/** Small "i" icon revealing `text` in a tooltip on hover/focus. Generic — drop next to any label that needs a short explanation. */
export default function InfoHint({
  text,
  className = "",
  align = "center",
}: InfoHintProps) {
  return (
    <span
      className={`group relative inline-flex cursor-help items-center ${className}`}
      tabIndex={0}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="size-3.5 text-gray-400 dark:text-gray-500"
      >
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
          clipRule="evenodd"
        />
      </svg>
      <span
        role="tooltip"
        className={`pointer-events-none absolute bottom-full z-50 mb-2 w-max max-w-[240px] whitespace-normal rounded-md bg-gray-900 px-2 py-1 text-center text-theme-xs font-medium text-white opacity-0 shadow-theme-sm transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100 dark:bg-gray-700 ${ALIGN_CLASSES[align]}`}
      >
        {text}
      </span>
    </span>
  );
}
