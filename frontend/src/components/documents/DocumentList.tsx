'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { StatusBadge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import {
  listDocuments,
  parseApiDate,
  type DocumentSummary,
} from '@/lib/documents';
import { cn } from '@/lib/cn';
import { toApiError } from '@/lib/errors';
import { formatBytes } from '@/lib/uploads';

const IN_PROGRESS = new Set(['queued', 'processing']);
const POLL_INTERVAL_MS = 4000;
const RETRY_INTERVAL_MS = 8000;

function formatDate(value: string | null): string {
  if (!value) return '';
  return parseApiDate(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

/**
 * The signed-in user's documents, newest first, with their processing
 * status. Built for the upload page (US-7: "the uploaded document appears in
 * my library"), and reusable by the dashboard library (US-3).
 *
 * Bump ``refreshKey`` to reload, e.g. after an upload finishes. While any
 * document is still queued or processing, the list also re-checks every few
 * seconds, so finished and failed documents update without a page reload.
 */
export function DocumentList({ refreshKey = 0 }: { refreshKey?: number }) {
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function load() {
      try {
        const docs = await listDocuments();
        if (!current) return;
        setDocuments(docs);
        setError(null);
        if (docs.some((doc) => doc.status && IN_PROGRESS.has(doc.status))) {
          timer = setTimeout(load, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (!current) return;
        // Keep whatever list is already on screen and try again shortly, so
        // a brief network or server hiccup recovers on its own.
        setError(toApiError(err).message);
        timer = setTimeout(load, RETRY_INTERVAL_MS);
      }
    }

    load();
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [refreshKey]);

  const warning = error && (
    <Alert tone="info">
      Couldn&apos;t refresh your documents ({error}) Trying again…
    </Alert>
  );

  if (documents === null) {
    if (warning) return warning;
    return (
      <div className="flex justify-center py-6 text-slate-500">
        <Spinner label="Loading your documents" />
      </div>
    );
  }
  if (documents.length === 0) {
    return (
      <div className="space-y-3">
        {warning}
        <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-center text-sm text-slate-600">
          No documents yet. Uploaded files will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {warning}
      <DocumentRows documents={documents} />
    </div>
  );
}

function DocumentRows({ documents }: { documents: DocumentSummary[] }) {
  return (
    <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
      {documents.map((doc) => (
        <li
          key={doc.id}
          className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-3"
        >
          <div className="min-w-0">
            <Link
              href={`/documents/${doc.id}`}
              className="block truncate font-medium text-slate-900 underline-offset-4 hover:underline"
            >
              {doc.filename}
            </Link>
            <p className="text-xs text-slate-500">
              {formatBytes(doc.file_size_bytes)}
              {doc.created_at && <> · Uploaded {formatDate(doc.created_at)}</>}
            </p>
            <FailureNote doc={doc} />
          </div>
          <StatusBadge status={doc.status} />
        </li>
      ))}
    </ul>
  );
}

/**
 * Why processing failed (US-11). The server only sends reasons written for
 * users. A completed document can also carry a note when some of its pages
 * failed; it stays "Completed" and the note is shown as a warning, not an
 * error.
 */
function FailureNote({ doc }: { doc: DocumentSummary }) {
  if (!doc.error_message) return null;
  const failed = doc.status === 'failed';
  return (
    <p
      className={cn(
        'mt-0.5 text-xs',
        failed ? 'text-red-700' : 'text-amber-800'
      )}
    >
      {!failed && 'Some pages could not be read: '}
      {doc.error_message}
    </p>
  );
}
