export default function SummaryText({ text }: { text: string }) {
  return (
    <p className="mt-3 rounded-card p-3 text-[11px] leading-relaxed text-gs-text-secondary" style={{
      background: 'rgba(244, 241, 235, 0.65)',
      backdropFilter: 'blur(6px)',
      WebkitBackdropFilter: 'blur(6px)',
      border: '1px solid rgba(214, 208, 196, 0.30)',
    }}>
      {text}
    </p>
  );
}
