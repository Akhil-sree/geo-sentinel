import { NavLink, Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useI18n } from "../../lib/i18n";
import { useUIStore } from "../../store/uiStore";
import { getZones, type Zone } from "../../api/zones";
import type { Lang } from "../../lib/translations";

const NAV_ITEMS = [
  { to: "/", key: "nav.commandCenter" },
  { to: "/reports", key: "nav.reports" },
  { to: "/alerts", key: "nav.alerts" },
  { to: "/roads", key: "nav.roads" },
  { to: "/weather", key: "nav.weather" },
  { to: "/emergency", key: "nav.emergency" },
  { to: "/sensors", key: "nav.sensors" },
  { to: "/satellite", key: "nav.satellite" },
  { to: "/health", key: "nav.health" },
  { to: "/data", key: "nav.data" },
  { to: "/insights", key: "nav.insights" },
  { to: "/about", key: "nav.about" },
];

const LANGS: { code: Lang; label: string }[] = [
  { code: "EN", label: "EN" },
  { code: "AS", label: "অস" },
  { code: "MN", label: "মণ" },
];

export default function TopBar() {
  const [now, setNow] = useState(new Date());
  const [zones, setZones] = useState<Zone[]>([]);
  const [districtOpen, setDistrictOpen] = useState(false);
  const { lang, setLang, t } = useI18n();
  const navigate = useNavigate();
  const selectZone = useUIStore((s) => s.selectZone);

  useEffect(() => {
    const iv = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    getZones().then(setZones).catch(() => {});
  }, []);

  const districts = [...new Set(zones.map((z) => z.district))].sort();

  const pickDistrict = (district: string) => {
    setDistrictOpen(false);
    const first = zones.find((z) => z.district === district);
    navigate("/");
    if (first) selectZone(first.id);
  };

  return (
    <header className="shrink-0">

      {/* ── Institutional command header ── */}
      <div className="flex h-[68px] items-center justify-between gap-4 px-5" style={{
        background: '#FFFFFF',
        borderBottom: '1px solid #E5E7EB',
      }}>

        {/* Left: institutional identity */}
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-lg" style={{
            background: '#F0F1EB',
            border: '1px solid #D6D0C4',
          }} aria-hidden>
            🇮🇳
          </div>
          <div className="hidden leading-tight md:block">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em]" style={{ color: '#075240' }}>
              India
            </p>
            <p className="text-[10px] uppercase tracking-wider" style={{ color: '#6B7A32' }}>
              Geo-Sciences Division
            </p>
          </div>
        </div>

        {/* Center: product focal point */}
        <div className="min-w-0 flex-1 text-center">
          <h1 className="truncate text-[20px] font-bold tracking-[0.16em]" style={{ color: '#1A3C2E' }}>
            GEO-SENTINEL
          </h1>
          <p className="hidden truncate text-[10px] font-medium tracking-[0.08em] uppercase sm:block" style={{ color: '#5F6B62' }}>
            Landslide Early Warning · North Eastern Region
          </p>
        </div>

        {/* Right: status cluster */}
        <div className="flex shrink-0 items-center gap-2.5">

          {/* Date & time (real clock) */}
          <div className="hidden text-right leading-tight xl:block" aria-label="Current time">
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: '#1A3C2E' }}>
              {now.toLocaleDateString("en-GB", {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </p>
            <p className="text-[11px] tabular-nums font-medium" style={{ color: '#5F6B62' }}>
              {now.toLocaleTimeString("en-GB", {
                hour: "2-digit",
                minute: "2-digit",
              })}{" "}
              IST
            </p>
          </div>

          {/* System status — static dot, institutional */}
          <div className="flex items-center gap-1.5 rounded-full px-2.5 py-1" style={{
            background: 'rgba(7, 82, 64, 0.08)',
            border: '1px solid rgba(7, 82, 64, 0.2)',
          }} role="status" aria-label={t("header.systemOnline")}>
            <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: '#075240' }} aria-hidden />
            <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: '#075240' }}>
              {t("header.systemOnline")}
            </span>
          </div>

        </div>
      </div>

      {/* ── Slim navigation bar ── */}
      <nav className="flex h-9 items-center justify-between gap-2 overflow-x-auto px-4" style={{
        background: '#FAFAF8',
        borderBottom: '1px solid #E5E7EB',
      }} aria-label="Primary">

        {/* Left: Navigation Links */}
        <div className="flex min-w-0 items-center">
          <Link
            to="/"
            title={t("nav.home")}
            aria-label={t("nav.home")}
            className="mr-1 flex h-6 w-6 shrink-0 items-center justify-center rounded text-[13px] transition hover:bg-black/5"
            style={{ color: '#5F6B62' }}
          >
            ◉
          </Link>

          {NAV_ITEMS.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className="shrink-0 px-2 py-1 text-[11px] font-semibold uppercase tracking-wider transition hover:text-[#1A3C2E]"
              style={({ isActive }) => ({
                color: isActive ? '#075240' : '#5F6B62',
                boxShadow: isActive ? 'inset 0 -2px 0 #075240' : 'none',
              })}
            >
              {t(n.key)}
            </NavLink>
          ))}
        </div>

        {/* Right: Language + district */}
        <div className="flex shrink-0 items-center gap-2">
          <div className="flex items-center rounded-full p-0.5" style={{ border: '1px solid #D6D0C4' }} role="group" aria-label="Language">
            {LANGS.map((l) => (
              <button
                key={l.code}
                onClick={() => setLang(l.code)}
                aria-pressed={lang === l.code}
                className="rounded-full px-2 py-0.5 text-[10px] font-semibold transition"
                style={{
                  background: lang === l.code ? '#075240' : 'transparent',
                  color: lang === l.code ? '#FFFFFF' : '#075240',
                }}
              >
                {l.label}
              </button>
            ))}
          </div>

          <div className="relative hidden sm:block">
            <button
              type="button"
              onClick={() => setDistrictOpen((o) => !o)}
              aria-haspopup="listbox"
              aria-expanded={districtOpen}
              className="flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium transition hover:bg-black/5"
              style={{ color: '#075240' }}
            >
              <span className="text-[10px]" aria-hidden>📍</span>
              Meghalaya
              <span className="text-[9px] opacity-50" aria-hidden>{districtOpen ? "▲" : "▼"}</span>
            </button>
            {districtOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setDistrictOpen(false)} />
                <div className="absolute right-0 z-50 mt-1 w-52 overflow-hidden rounded-lg bg-white shadow-lg" style={{ border: '1px solid #E5E7EB' }} role="listbox">
                  {districts.length === 0 && (
                    <p className="px-4 py-3 text-[12px] text-gs-text-secondary">Loading districts…</p>
                  )}
                  {districts.map((d) => (
                    <button
                      key={d}
                      onClick={() => pickDistrict(d)}
                      className="block w-full px-4 py-2 text-left text-[13px] transition hover:bg-gs-surface-soft"
                      style={{ color: '#1A3C2E' }}
                      role="option"
                      aria-selected="false"
                    >
                      {d}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

      </nav>

    </header>
  );
}
