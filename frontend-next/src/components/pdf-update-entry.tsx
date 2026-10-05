"use client";

import DocumentDropzone from "./document-dropzone";
import { preparePdfUpdate } from "../lib/pdf-update-handoff";

export default function PdfUpdateEntry({ cupId, cupName }: { cupId: number; cupName: string }) {
  function openReview(files: File[]) {
    if (!files.length) return;
    preparePdfUpdate(cupId, files);
    window.location.hash = "import";
  }

  return <section className="admin-panel cn-pdf-update-entry" aria-labelledby="pdf-update-entry-title">
    <h2 id="pdf-update-entry-title">Uppdatera med ny PDF</h2>
    <p>Har du ett nytt spelschema för <strong>{cupName}</strong>? Släpp filen här eller välj den från din enhet. Du får granska nya matchtider och planer innan du sparar.</p>
    <DocumentDropzone files={[]} onFiles={openReview} buttonLabel="Välj PDF"/>
    <a href="#import">Öppna PDF-uppdatering →</a>
  </section>;
}
