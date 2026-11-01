import { useState } from "react";
import { api, ApiError } from "../lib/api";

// PDF upload: text-based PDFs only, extracted server-side with page
// references, then inserted as a pasted source through the existing
// evidence pipeline. Scanned/image PDFs are rejected by the backend.
export function PdfUpload({ onAdd }: { onAdd: (title: string, text: string) => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  const upload = async (file: File) => {
    setError(null);
    setDone(null);
    if (file.size > 5 * 1024 * 1024) {
      setError("PDF is larger than the 5 MB limit.");
      return;
    }
    setLoading(true);
    try {
      const result = await api.pdfText(file);
      onAdd(`PDF: ${result.filename}`, result.text);
      setDone(
        `Extracted ${result.pages_with_text} of ${result.pages} pages, ${result.total_chars.toLocaleString()} characters. Added as a pasted source with [Page N] markers, so evidence quotes carry their page.`,
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "PDF extraction failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-2xl border border-line bg-card p-5 shadow-card">
      <h2 className="font-display text-xl">Upload a PDF document</h2>
      <p className="mt-1 text-sm text-inksoft">
        Text-based PDFs only, up to 5 MB and 50 pages. Scanned or image-based PDFs have no extractable text and
        are rejected. The file is processed per request and is not stored on the server.
      </p>
      <input
        type="file"
        accept="application/pdf,.pdf"
        aria-label="Upload a PDF document"
        disabled={loading}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void upload(file);
          e.target.value = "";
        }}
        className="mt-3 block w-full text-sm"
      />
      {loading && <p className="mt-2 text-sm text-inksoft">Extracting PDF text…</p>}
      {error && (
        <p role="alert" className="mt-3 rounded-xl border border-coral/40 bg-coral/5 p-3 text-sm text-coral">
          {error}
        </p>
      )}
      {done && <p className="mt-3 rounded-xl border border-line bg-cream p-3 text-sm">{done}</p>}
    </section>
  );
}
