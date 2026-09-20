export default function Spinner({ size = 28 }: { size?: number }) {
  return (
    <div style={{ width: size, height: size }}
      className="animate-spin rounded-full border-2 border-gs-border border-t-forest"
      role="status" aria-label="loading" />
  );
}
