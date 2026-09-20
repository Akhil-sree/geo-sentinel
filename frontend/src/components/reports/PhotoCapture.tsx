import { useState } from "react";
import { validateFile, compressImage } from "../../lib/photo";

export default function PhotoCapture({ onPhoto }: { onPhoto: (b: Blob | null) => void }) {
  const [preview, setPreview] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const onChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    setErr(null); onPhoto(null); setPreview(null);
    const f = e.target.files?.[0];
    if (!f) return;
    const problem = validateFile(f);
    if (problem) { setErr(problem); return; }
    try {
      if (f.type.startsWith("video/")) { onPhoto(f); return; }
      const blob = await compressImage(f);
      setPreview(URL.createObjectURL(blob));
      onPhoto(blob);
    } catch { setErr("Could not process this image"); }
  };

  return (
    <div>
      <label className="block text-[10px] font-medium text-gs-text-secondary">Photo / video (optional, ≤25MB video)</label>
      <input type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm" onChange={onChange}
        className="mt-1 w-full rounded-card border border-gs-border bg-white
                   p-2 text-[11px] file:mr-2 file:rounded-card file:border-0 file:bg-forest file:px-2 file:py-1 file:text-white file:text-[10px] file:font-medium" />
      {preview && <img src={preview} alt="preview" className="mt-2 max-h-36 rounded-card" />}
      {err && <p className="mt-1 text-[10px] text-risk-critical">{err}</p>}
    </div>
  );
}
