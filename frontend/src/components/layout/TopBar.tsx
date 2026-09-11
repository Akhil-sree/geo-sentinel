import { NavLink, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import LowBandwidthToggle from "../common/LowBandwidthToggle";

const NAV = [
  { to: "/", label: "COMMAND CENTER", icon: "◎" },
  { to: "/dashboard", label: "RISK DASHBOARD", icon: "▦" },
  { to: "/roads", label: "ROADS", icon: "▤" },
  { to: "/weather", label: "WEATHER", icon: "☁" },
  { to: "/emergency", label: "EMERGENCY", icon: "⚠" },
  { to: "/reports", label: "REPORTS", icon: "▣" },
  { to: "/alerts", label: "ALERTS", icon: "✉" },
  { to: "/insights", label: "DATA & INSIGHTS", icon: "📊" },
  { to: "/about", label: "ABOUT", icon: "ⓘ" },
];

export default function TopBar() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const iv = setInterval(() => setNow(new Date()), 30000);

    return () => clearInterval(iv);
  }, []);

  return (
    <header className="shrink-0">

      {/* =====================================================
          GOVERNMENT HEADER
      ====================================================== */}
      <div className="flex min-h-[64px] items-center justify-between bg-white px-5 py-2 shadow-sm">

        {/* Government Identity */}
        <div className="flex items-center gap-3 text-[10px] leading-tight text-[#404943]">

          {/* Indian Flag */}
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#f5f5f5] text-xl">
            🇮🇳
          </div>

          <div>
            <p className="font-semibold text-[#1b1c17]">
              भारत सरकार
            </p>

            <p>
              Government of India
            </p>

            <p className="text-[9px] text-[#707973]">
              Geo-Sciences Division
            </p>
          </div>
        </div>


        {/* =================================================
            GEO-SENTINEL BRAND
        ================================================== */}
        <div className="text-center">

          <h1 className="font-headline text-2xl font-bold tracking-[0.18em] text-[#04442f]">
            GEO-SENTINEL
          </h1>

          <p className="mt-0.5 text-[10px] font-semibold tracking-wide text-[#404943]">
            Landslide Early Warning System · India
          </p>

          <p className="text-[9px] text-[#707973]">
            A Digital India Initiative
          </p>

        </div>


        {/* =================================================
            RIGHT SIDE STATUS
        ================================================== */}
        <div className="flex items-center gap-5">

          {/* Digital India */}
          <div className="hidden text-right leading-tight sm:block">
            <p className="text-[10px] font-bold text-[#1b1c17]">
              Digital India
            </p>

            <p className="text-[9px] text-[#707973]">
              Power to Empower
            </p>
          </div>


          {/* Date + Time */}
          <div className="text-right text-[9px] leading-tight text-[#707973]">

            <p className="font-semibold text-[#404943]">
              {now.toLocaleDateString("en-GB", {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </p>

            <p>
              {now.toLocaleTimeString("en-GB", {
                hour: "2-digit",
                minute: "2-digit",
              })}{" "}
              IST
            </p>

          </div>


          {/* System Status */}
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-[9px] font-bold text-[#04442f]">

            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>

            SYSTEM ONLINE

          </div>

        </div>

      </div>


      {/* =====================================================
          MAIN NAVIGATION
      ====================================================== */}
      <nav className="flex min-h-[34px] items-center justify-between bg-[#0a2f52] px-4 text-white shadow-sm">

        {/* Left Navigation */}
        <div className="flex items-center gap-1">

          {/* Home */}
          <Link
            to="/"
            title="Home"
            className="flex items-center justify-center rounded bg-[#1d4e79] px-3 py-1.5 text-[11px] font-bold transition hover:bg-[#28628f]"
          >
            ⌂
          </Link>


          {/* Navigation Links */}
          {NAV.map((n) => (
            <NavLink
              key={n.label}
              to={n.to}
              className={({ isActive }) =>
                `rounded px-3 py-1.5 text-[10px] font-semibold tracking-wide transition ${
                  isActive
                    ? "bg-white/15 text-white shadow-sm"
                    : "text-sky-100 hover:bg-white/10 hover:text-white"
                }`
              }
            >
              <span className="mr-1">
                {n.icon}
              </span>

              {n.label}
            </NavLink>
          ))}

        </div>


        {/* =================================================
            LOCATION SELECTOR
        ================================================== */}
        <div className="flex items-center gap-2">
          <LowBandwidthToggle />
          <button
            type="button"
            className="flex items-center gap-1 rounded px-3 py-1.5 text-[10px] font-semibold text-sky-100 transition hover:bg-white/10"
          >
            📍 Meghalaya
            <span className="text-[9px] opacity-70">▼</span>
          </button>
        </div>

      </nav>

    </header>
  );
}
