import type { CSSProperties } from "react";
import styles from "./PulseLoader.module.css";

type PulseLoaderProps = {
  size?: number;
  speed?: number;
  color?: string;
  darkColor?: string;
  className?: string;
};

/** Raw pulse animation. Prefer PageLoading / InlineLoading for labeled UX. */
export default function PulseLoader({
  size = 45,
  speed = 2,
  color = "#1d2939",
  darkColor = "#f2f4f7",
  className = "",
}: PulseLoaderProps) {
  const style = {
    "--uib-size": `${size}px`,
    "--uib-speed": `${speed}s`,
    "--uib-color": color,
    "--uib-color-dark": darkColor,
  } as CSSProperties;

  return (
    <div
      className={`${styles.pulse} ${className}`.trim()}
      style={style}
      aria-hidden
    />
  );
}
