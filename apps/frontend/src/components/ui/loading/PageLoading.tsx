import PulseLoader from "./PulseLoader";

type PageLoadingProps = {
  /** Spanish label for screen readers (not shown visually). */
  label: string;
  /** Layout escape hatch. Default: full viewport. Use `flex-1` in flex shells. */
  className?: string;
};

export default function PageLoading({
  label,
  className = "min-h-screen",
}: PageLoadingProps) {
  return (
    <div
      role="status"
      aria-busy="true"
      className={`flex w-full items-center justify-center ${className}`}
    >
      <PulseLoader
        size={45}
        speed={2}
        color="#1d2939"
        darkColor="#f2f4f7"
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}
