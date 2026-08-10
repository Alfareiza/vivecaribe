"use client";

import React, { useState } from "react";
import { Dropdown } from "@/components/ui/dropdown/Dropdown";
import { MoreDotIcon } from "@/icons";

export type ShareMenuOption = {
  id: string;
  label: string;
  icon?: React.ReactNode;
  href?: string | null;
  disabled?: boolean;
};

type ShareMenuProps = {
  options: ShareMenuOption[];
  /** Accessible name for the trigger. */
  label?: string;
  className?: string;
};

/**
 * Share trigger + TailAdmin Dropdown. Same chrome everywhere; options are slottable.
 */
export default function ShareMenu({
  options,
  label = "Compartir",
  className = "",
}: ShareMenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  function close() {
    setIsOpen(false);
  }

  return (
    <div className={`relative inline-block ${className}`.trim()}>
      <button
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
        className="dropdown-toggle inline-flex h-9 w-9 mr-4 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800 dark:text-gray-400 dark:hover:bg-white/5 dark:hover:text-white/90"
      >
        <MoreDotIcon className="size-5" />
      </button>
      <Dropdown
        isOpen={isOpen}
        onClose={close}
        className="w-52 p-2"
      >
        <div role="menu" aria-label={label}>
          {options.map((option) => {
            const content = (
              <span className="flex items-center gap-2.5">
                {option.icon ? (
                  <span className="inline-flex size-5 shrink-0 items-center justify-center overflow-visible [&>svg]:h-5 [&>svg]:w-5 [&>svg]:overflow-visible [&>svg]:shrink-0">
                    {option.icon}
                  </span>
                ) : null}
                <span>{option.label}</span>
              </span>
            );

            if (option.disabled || !option.href) {
              return (
                <button
                  key={option.id}
                  type="button"
                  role="menuitem"
                  disabled
                  className="flex w-full cursor-not-allowed rounded-lg px-3 py-2 text-left text-sm font-normal text-gray-300 dark:text-gray-600"
                >
                  {content}
                </button>
              );
            }

            return (
              <a
                key={option.id}
                role="menuitem"
                href={option.href}
                target="_blank"
                rel="noopener noreferrer"
                onClick={close}
                className="flex w-full rounded-lg px-3 py-2 text-left text-sm font-normal text-gray-600 hover:bg-gray-100 hover:text-gray-800 dark:text-gray-400 dark:hover:bg-white/5 dark:hover:text-gray-200"
              >
                {content}
              </a>
            );
          })}
        </div>
      </Dropdown>
    </div>
  );
}
