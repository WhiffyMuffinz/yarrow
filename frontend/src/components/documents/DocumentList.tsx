'use client';

import Link from 'next/link';
import { useEffect, useId, useRef, useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { StatusBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import {
  listDocuments,
  parseApiDate,
  cancelProcessing,
  renameDocument,
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
      <DocumentRows
        documents={documents}
        onChanged={(changed) =>
          setDocuments((current) =>
            (current ?? []).map((doc) =>
              doc.id === changed.id ? changed : doc
            )
          )
        }
      />
    </div>
  );
}

function DocumentRows({
  documents,
  onChanged,
}: {
  documents: DocumentSummary[];
  onChanged: (doc: DocumentSummary) => void;
}) {
  return (
    <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
      {documents.map((doc) => (
        <DocumentRow key={doc.id} doc={doc} onChanged={onChanged} />
      ))}
    </ul>
  );
}

/** Mirrors the server's rules, so most mistakes are caught before sending. */
function checkName(name: string): string | null {
  if (!name) return 'Name cannot be empty.';
  if (name.length > 255) return 'Name must be 255 characters or fewer.';
  // eslint-disable-next-line no-control-regex
  if (/[\\/\u0000-\u001f\u007f]/.test(name)) {
    return 'Name cannot contain slashes or control characters.';
  }
  return null;
}

function DocumentRow({
  doc,
  onChanged,
}: {
  doc: DocumentSummary;
  onChanged: (doc: DocumentSummary) => void;
}) {
  const inputId = useId();
  const errorId = useId();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(doc.filename);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const renameButton = useRef<HTMLButtonElement>(null);
  const [canceling, setCanceling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  async function cancel() {
    setCanceling(true);
    setCancelError(null);
    try {
      onChanged(await cancelProcessing(doc.id));
    } catch (err) {
      // Usually a worker picked it up first; the list's next refresh will
      // show it as processing.
      setCancelError(toApiError(err).message);
    } finally {
      setCanceling(false);
    }
  }

  function startEditing() {
    setDraft(doc.filename);
    setError(null);
    setEditing(true);
  }

  function stopEditing() {
    setEditing(false);
    setError(null);
    // Put focus back where the user started.
    requestAnimationFrame(() => renameButton.current?.focus());
  }

  async function save() {
    const name = draft.trim();
    if (name === doc.filename) return stopEditing();
    const problem = checkName(name);
    if (problem) return setError(problem);
    setSaving(true);
    try {
      onChanged(await renameDocument(doc.id, name));
      stopEditing();
    } catch (err) {
      // The old name stays; say why the new one wasn't saved (US-39).
      const apiError = toApiError(err);
      setError(apiError.fields.filename ?? apiError.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <li className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-3">
      <div className="min-w-0 flex-1">
        {editing ? (
          <form
            className="space-y-1"
            onSubmit={(event) => {
              event.preventDefault();
              save();
            }}
          >
            <label htmlFor={inputId} className="sr-only">
              New name for {doc.filename}
            </label>
            <div className="flex flex-wrap items-center gap-2">
              <input
                id={inputId}
                value={draft}
                maxLength={255}
                autoFocus
                disabled={saving}
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? errorId : undefined}
                onChange={(event) => setDraft(event.target.value)}
                onFocus={(event) => {
                  // Select the name but not the extension, so typing
                  // replaces "report" in "report.pdf".
                  const dot = event.target.value.lastIndexOf('.');
                  event.target.setSelectionRange(
                    0,
                    dot > 0 ? dot : event.target.value.length
                  );
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Escape') stopEditing();
                }}
                className={cn(
                  'min-w-0 flex-1 rounded-lg border px-2 py-1 text-sm text-slate-900',
                  error ? 'border-red-600' : 'border-slate-300'
                )}
              />
              <Button type="submit" className="w-auto px-3" loading={saving}>
                Save
              </Button>
              <Button
                type="button"
                variant="secondary"
                className="w-auto px-3"
                disabled={saving}
                onClick={stopEditing}
              >
                Cancel
              </Button>
            </div>
            {error && (
              <p id={errorId} role="alert" className="text-xs text-red-700">
                {error}
              </p>
            )}
          </form>
        ) : (
          <Link
            href={`/documents/${doc.id}`}
            className="block truncate font-medium text-slate-900 underline-offset-4 hover:underline"
          >
            {doc.filename}
          </Link>
        )}
        <p className="text-xs text-slate-500">
          {formatBytes(doc.file_size_bytes)}
          {doc.created_at && <> · Uploaded {formatDate(doc.created_at)}</>}
        </p>
        <FailureNote doc={doc} />
        {cancelError && (
          <p role="alert" className="mt-0.5 text-xs text-red-700">
            {cancelError}
          </p>
        )}
      </div>
      <div className="flex items-center gap-3">
        {/* Only while queued: a started or finished job can't be canceled. */}
        {doc.status === 'queued' && !editing && (
          <Button
            variant="link"
            onClick={cancel}
            loading={canceling}
            aria-label={`Cancel processing of ${doc.filename}`}
          >
            Cancel
          </Button>
        )}
        {!editing && (
          <Button
            ref={renameButton}
            variant="link"
            onClick={startEditing}
            aria-label={`Rename ${doc.filename}`}
          >
            Rename
          </Button>
        )}
        <StatusBadge status={doc.status} />
      </div>
    </li>
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
