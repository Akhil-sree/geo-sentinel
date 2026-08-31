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
      const blob = await compressImage(f);           // downscale + JPEG recompress
      setPreview(URL.createObjectURL(blob));
      onPhoto(blob);
    } catch { setErr("Could not process this image"); }
  };

  return (
    <div>
      <label className="block text-xs font-semibold text-slate-400">Photo (optional)</label>
      <input type="file" accept="image/jpeg,image/png,image/webp" onChange={onChange}
        className="mt-1 w-full rounded border border-slate-700 bg-slate-900
                   p-2 text-xs file:mr-2 file:rounded file:border-0 file:bg-sky-700 file:px-2 file:py-1" />
      {preview && <img src={preview} alt="preview" className="mt-2 max-h-36 rounded" />}
      {err && <p className="mt-1 text-xs text-red-400">{err}</p>}
    </div>
  );
}
