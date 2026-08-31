// Card.tsx
export default function Card({ title, children, className = "" }: {
  title?: string; children: React.ReactNode; className?: string;
}) {
  return (
    <div className={`rounded-lg border border-slate-800 bg-slate-900/50 p-3 ${className}`}>
      {title && <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h3>}
      {children}
    </div>
  );
}
