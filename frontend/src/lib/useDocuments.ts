'use client';

import { useCallback, useEffect, useState } from 'react';
import { listDocuments, type DocumentSummary } from './documents';
import { toApiError } from './errors';

const IN_PROGRESS = new Set(['queued', 'processing']);
const POLL_INTERVAL_MS = 4000;
const RETRY_INTERVAL_MS = 8000;

/**
 * The signed-in user's documents, newest first.
 *
 * Bump refreshKey to reload, e.g. after an upload finishes. While any
 * document is still queued or processing, the list also re-checks every few
 * seconds, so finished and failed documents update without a page reload. A
 * failed load keeps whatever list is already on screen and retries shortly,
 * so a brief network or server hiccup recovers on its own.
 */
export function useDocuments(refreshKey = 0) {
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

  /** Swap in a document the server just returned, e.g. after a rename. */
  const replace = useCallback((changed: DocumentSummary) => {
    setDocuments((current) =>
      (current ?? []).map((doc) => (doc.id === changed.id ? changed : doc))
    );
  }, []);

  return { documents, error, replace };
}
