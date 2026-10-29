import { afterEach, expect, it, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import SearchPage from './page';
import type { SearchHit } from '@/lib/search';

vi.mock('@/lib/search', () => ({ searchDocuments: vi.fn() }));

import { searchDocuments } from '@/lib/search';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function hit(snippet: { edited?: boolean }): SearchHit[] {
  return [
    {
      id: 'doc-1',
      filename: 'notes.pdf',
      snippets: [
        {
          region_id: 'r1',
          page_number: 1,
          text: 'the quarterly summary',
          match_start: 4,
          match_end: 13,
          ...snippet,
        },
      ],
    },
  ];
}

it('flags snippets that come from corrected regions', async () => {
  vi.mocked(searchDocuments).mockResolvedValue(hit({ edited: true }));
  render(<SearchPage />);
  fireEvent.change(screen.getByLabelText(/Search/), {
    target: { value: 'quarterly' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Search' }));

  await waitFor(() => {
    expect(screen.getByText('corrected')).toBeTruthy();
  });
});

it('does not flag untouched snippets', async () => {
  vi.mocked(searchDocuments).mockResolvedValue(hit({}));
  render(<SearchPage />);
  fireEvent.change(screen.getByLabelText(/Search/), {
    target: { value: 'quarterly' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Search' }));

  await waitFor(() => {
    expect(screen.getByText('quarterly')).toBeTruthy();
  });
  expect(screen.queryByText('corrected')).toBeNull();
});
