"use client";

import Image from "next/image";

type ProviderLogoProps = {
  provider: string;
  size?: number;
  className?: string;
};

/** Circular booking-provider mark used in the reservas table and detail modal. */
export default function ProviderLogo({
  provider,
  size = 28,
  className = "",
}: ProviderLogoProps) {
  return (
    <span
      className={`inline-flex shrink-0 overflow-hidden rounded-full border border-gray-200 dark:border-gray-800 ${className}`.trim()}
      style={{ width: size, height: size }}
    >
      <Image
        width={size}
        height={size}
        src={`/images/providers/${provider}.svg`}
        alt={provider}
        className="h-full w-full object-cover"
      />
    </span>
  );
}
