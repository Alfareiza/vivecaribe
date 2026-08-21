"use client";

import React, { useState } from "react";
import Label from "@/components/form/Label";
import TextArea from "@/components/form/input/TextArea";
import Button from "@/components/ui/button/Button";
import { Modal } from "@/components/ui/modal";

type ConfirmDialogTextInput = {
  label: string;
  placeholder?: string;
  maxLength?: number;
  required?: boolean;
};

type ConfirmDialogProps = {
  isOpen: boolean;
  title: string;
  description?: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Renders the confirm button in error styling for a destructive action. */
  destructive?: boolean;
  /** When set, shows a required-by-default textarea whose value is passed to `onConfirm`. */
  textInput?: ConfirmDialogTextInput;
  loading?: boolean;
  error?: string | null;
  onConfirm: (value: string) => void;
  onClose: () => void;
};

/** Generic confirm-with-optional-reason modal — no built-in confirm dialog exists elsewhere in this codebase. */
export default function ConfirmDialog({
  isOpen,
  title,
  description,
  confirmLabel = "Confirmar",
  cancelLabel = "Salir",
  destructive = false,
  textInput,
  loading = false,
  error,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  const [value, setValue] = useState("");
  // Reset the textarea when the dialog transitions closed -> open, without
  // an effect (this component stays mounted; only `isOpen` toggles).
  const [wasOpen, setWasOpen] = useState(isOpen);
  if (isOpen !== wasOpen) {
    setWasOpen(isOpen);
    if (isOpen) setValue("");
  }

  const isValid = !textInput?.required || value.trim().length > 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      className="m-4 max-w-[440px] p-5 sm:p-6"
    >
      <h4 className="mb-2 pr-8 text-title-sm font-semibold text-gray-800 dark:text-white/90">
        {title}
      </h4>
      {description ? (
        <p className="mb-4 text-theme-sm text-gray-500 dark:text-gray-400">
          {description}
        </p>
      ) : null}
      {textInput ? (
        <div className="mb-4">
          <Label>{textInput.label}</Label>
          <TextArea
            value={value}
            onChange={(next) =>
              setValue(
                textInput.maxLength ? next.slice(0, textInput.maxLength) : next,
              )
            }
            rows={3}
            placeholder={textInput.placeholder}
          />
          {textInput.maxLength ? (
            <p className="mt-1 text-right text-theme-xs text-gray-400 dark:text-gray-500">
              {value.length}/{textInput.maxLength}
            </p>
          ) : null}
        </div>
      ) : null}
      {error ? (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-error-200 bg-error-50 px-3 py-2 text-theme-sm text-error-700 dark:border-error-500/30 dark:bg-error-500/10 dark:text-error-400"
        >
          {error}
        </p>
      ) : null}
      <div className="flex items-center justify-end gap-3">
        <Button size="sm" variant="outline" onClick={onClose} disabled={loading}>
          {cancelLabel}
        </Button>
        <Button
          size="sm"
          onClick={() => onConfirm(value.trim())}
          disabled={loading || !isValid}
          className={
            destructive ? "!bg-error-500 hover:!bg-error-600" : undefined
          }
        >
          {loading ? "Procesando…" : confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
