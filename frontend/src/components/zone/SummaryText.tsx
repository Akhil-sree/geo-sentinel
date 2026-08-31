/** Plain-language summary generated strictly from backend model outputs —
 *  the frontend never invents explanation beyond what the API returned. */
export default function SummaryText({ text }: { text: string }) {
  return (
    <p className="mt-3 rounded border border-slate-800 bg-slate-900/50 p-2.5
                  text-xs leading-relaxed text-slate-300">
      {text}
    </p>
  );
}
