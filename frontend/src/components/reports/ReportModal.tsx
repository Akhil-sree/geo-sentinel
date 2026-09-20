import { useState } from "react";
import { Modal } from "../common/Modal";
import PhotoCapture from "./PhotoCapture";
import GpsCapture from "./GpsCapture";
import OfflineToggle from "./OfflineToggle";
import { useReportQueue } from "../../hooks/useReportQueue";
import { useToast } from "../common/Toast";

export default function ReportModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [photo, setPhoto] = useState<Blob | null>(null);
  const [fix, setFix] = useState<{ lat: number; lng: number } | null>(null);
  const [type, setType] = useState("debris_flow");
  const [sev, setSev] = useState("minor");
  const [desc, setDesc] = useState("");
  const [manual, setManual] = useState("");
  const { submit, queued, online } = useReportQueue();
  const toast = useToast();

  const canSubmit = (fix || manual.trim()) && desc.trim().length > 0;

  const onSubmit = async () => {
    const [lat, lng] = fix
      ? [fix.lat, fix.lng]
      : manual.split(",").map(Number);
    if (!isFinite(lat) || !isFinite(lng)) { toast("Invalid coordinates", "err"); return; }

    const rep = {
      id: crypto.randomUUID(),
      photoBlob: photo,
      queuedAt: new Date().toISOString(),
      attempts: 0,
      payload: {
        latitude: lat, longitude: lng,
        landslide_type: type, severity_observed: sev,
        description: desc.trim(), client_timestamp: new Date().toISOString(),
      },
    };
    const ok = await submit(rep);
    toast(ok ? "Report submitted — PENDING moderation"
             : "Offline — queued, will auto-sync", ok ? "ok" : "ok");
    setDesc(""); setPhoto(null); setFix(null); setManual("");
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="Report a landslide">
      <div className="space-y-3">
        <GpsCapture onFix={setFix} />
        {!fix && (
          <input value={manual} onChange={(e) => setManual(e.target.value)}
            placeholder="or lat,lng (e.g. 25.30, 91.70)"
            className="w-full rounded-card border border-gs-border bg-white p-2.5 text-[11px] text-gs-text" />
        )}
        <div className="grid grid-cols-2 gap-2">
          <select value={type} onChange={(e) => setType(e.target.value)}
            className="rounded-card border border-gs-border bg-white p-2.5 text-[11px] text-gs-text">
            <option value="debris_flow">Debris flow</option>
            <option value="rotational_slump">Rotational slump</option>
            <option value="rockfall">Rockfall</option>
            <option value="road_cut_failure">Road-cut failure</option>
          </select>
          <select value={sev} onChange={(e) => setSev(e.target.value)}
            className="rounded-card border border-gs-border bg-white p-2.5 text-[11px] text-gs-text">
            <option value="minor">Minor</option>
            <option value="significant">Significant</option>
            <option value="major">Major</option>
          </select>
        </div>
        <textarea value={desc} onChange={(e) => setDesc(e.target.value)} rows={3}
          placeholder="What did you observe?"
          className="w-full rounded-card border border-gs-border bg-white p-2.5 text-[11px] text-gs-text" />
        <PhotoCapture onPhoto={setPhoto} />
        <OfflineToggle />
        <button onClick={onSubmit} disabled={!canSubmit}
          className="w-full rounded-card bg-forest py-2.5 text-[11px] font-semibold text-white transition hover:bg-forest-800 disabled:opacity-40 active:scale-[0.98]">
          {online ? "Submit" : `Queue (${queued} pending)`}
        </button>
      </div>
    </Modal>
  );
}
