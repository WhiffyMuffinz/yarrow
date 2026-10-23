'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { Alert } from '@/components/ui/Alert';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { toApiError } from '@/lib/errors';
import {
  FILTERABLE_KINDS,
  WARNING_KINDS,
  listWarnings,
  warningDetail,
  warningHref,
  warningKind,
  warningLabel,
  type WarningEntry,
  type WarningKind,
} from '@/lib/warnings';

type Load =
  | { state: 'loading' }
  | { state: 'ready'; warnings: WarningEntry[] }
  | { state: 'error'; message: string };

function Warnings() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [load, setLoad] = useState<Load>({ state: 'loading' });

  const typeParam = searchParams.get('type');
  const type = FILTERABLE_KINDS.includes(typeParam as WarningKind)
    ? (typeParam as WarningKind)
    : null;

  useEffect(() => {
    let current = true;
    listWarnings()
      .then((warnings) => {
        if (current) setLoad({ state: 'ready', warnings });
      })
      .catch((err) => {
        if (current)
          setLoad({ state: 'error', message: toApiError(err).message });
      });

    return () => {
      current = false;
    };
  }, []);

  function onTypeChange(value: string) {
    router.replace(value ? `/warnings?type=${value}` : '/warnings', {
      scroll: false,
    });
  }

  const shown =
    load.state === 'ready'
      ? load.warnings.filter(
          (warning) => !type || warningKind(warning.message) === type
        )
      : [];

  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Warnings
        </h1>
        <p className="text-sm text-slate-600">
          Pages whose scan quality may have affected extraction. Open one to
          check it against the original.
        </p>
      </div>

      {load.state === 'loading' && (
        <div className="flex justify-center py-8 text-slate-500">
          <Spinner label="Loading warnings" />
        </div>
      )}

      {load.state === 'error' && <Alert>{load.message}</Alert>}

      {load.state === 'ready' && load.warnings.length === 0 && (
        <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-center text-sm text-slate-600">
          No quality warnings. Your scans look good.
        </p>
      )}

      {load.state === 'ready' && load.warnings.length > 0 && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="w-full sm:w-56">
              <Select
                id="warnings-type"
                label="Warning type"
                value={type ?? ''}
                onChange={(event) => onTypeChange(event.target.value)}
              >
                <option value="">All types</option>
                {FILTERABLE_KINDS.map((kind) => (
                  <option key={kind} value={kind}>
                    {WARNING_KINDS[kind].label}
                  </option>
                ))}
              </Select>
            </div>
            <p
              aria-live="polite"
              className="text-sm tabular-nums text-slate-600"
            >
              {type
                ? `${shown.length} of ${load.warnings.length} warnings`
                : `${load.warnings.length} ${load.warnings.length === 1 ? 'warning' : 'warnings'}`}
            </p>
          </div>

          {shown.length === 0 ? (
            <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-center text-sm text-slate-600">
              No warnings of this type.
            </p>
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <div
                aria-hidden="true"
                className={`hidden border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-medium text-slate-500 md:grid md:grid-cols-[9rem_minmax(0,1fr)_minmax(0,14rem)_3.5rem_1rem] md:items-center md:gap-4`}
              >
                <span>Warning</span>
                <span>Details</span>
                <span>Document</span>
                <span className="text-right">Page</span>
                <span />
              </div>
              <ul>
                {shown.map((warning, index) => (
                  <li
                    key={`${warning.document_id}-${warning.page_number}-${index}`}
                    className="border-t border-slate-100 first:border-t-0"
                  >
                    <Link
                      href={warningHref(
                        warning.document_id,
                        warning.page_number
                      )}
                      className={`flex items-center gap-3 px-4 py-3 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-slate-900 md:grid md:grid-cols-[9rem_minmax(0,1fr)_minmax(0,14rem)_3.5rem_1rem] md:items-center md:gap-4`}
                    >
                      <div className="min-w-0 flex-1 space-y-1 md:contents">
                        <span className="inline-flex w-fit rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-900 ring-1 ring-inset ring-amber-200">
                          {warningLabel(warning.message)}
                        </span>
                        <span
                          title={warningDetail(warning.message)}
                          className="hidden truncate text-sm text-slate-600 md:block"
                        >
                          {warningDetail(warning.message)}
                        </span>
                        <span className="flex min-w-0 gap-1 text-sm text-slate-900 md:contents">
                          <span title={warning.filename} className="truncate">
                            {warning.filename}
                          </span>
                          <span className="shrink-0 text-slate-500 md:hidden">
                            · Page {warning.page_number}
                          </span>
                          <span className="hidden text-right tabular-nums md:block">
                            <span className="sr-only">Page </span>
                            {warning.page_number}
                          </span>
                        </span>
                      </div>
                      <ChevronRight
                        aria-hidden="true"
                        className="size-4 shrink-0 text-slate-400"
                      />
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function WarningsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-8 text-slate-500">
          <Spinner label="Loading warnings" />
        </div>
      }
    >
      <Warnings />
    </Suspense>
  );
}
