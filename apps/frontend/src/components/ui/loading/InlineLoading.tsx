import PulseLoader from "./PulseLoader";

type InlineLoadingProps = {
  /** Spanish label for screen readers (not shown visually). */
  label: string;
};

export default function InlineLoading({ label }: InlineLoadingProps) {
  return (
    <div
      role="status"
      aria-busy="true"
      className="flex items-center justify-center py-6"
    >
      <PulseLoader
        size={36}
        speed={2}
        color="#1d2939"
        darkColor="#f2f4f7"
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}
