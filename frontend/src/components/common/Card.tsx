export default function Card({ title, children, className = "" }: {
  title?: string; children: React.ReactNode; className?: string;
}) {
  return (
    <div className={`rounded-card p-3.5 ${className}`} style={{
  background: 'rgba(255, 255, 255, 0.55)',
  backdropFilter: 'blur(4px)',
  WebkitBackdropFilter: 'blur(4px)',
  border: '1px solid rgba(255, 255, 255, 0.30)',
  boxShadow: '0 2px 10px rgba(15, 35, 27, 0.04)',
    }}>
      {title && <h3 className="mb-2 text-[11px] font-medium text-gs-text-secondary">{title}</h3>}
      {children}
    </div>
  );
}
