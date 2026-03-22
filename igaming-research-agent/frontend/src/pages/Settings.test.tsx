import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Settings from '@/pages/Settings';
import * as apiService from '@/services/api';


describe('Settings', () => {
  it('can add, toggle active state, and delete queries', async () => {
    const queries = [
      {
        id: 1,
        search_term: 'Initial term',
        stream_type: 'legislative',
        description: 'desc',
        is_active: true,
        created_at: '2026-03-22T00:00:00Z',
        updated_at: '2026-03-22T00:00:00Z',
      },
    ] as any[];

    vi.spyOn(apiService, 'getQueries').mockImplementation(async () => [...queries]);
    vi.spyOn(apiService, 'createQuery').mockImplementation(async (payload: any) => {
      const item = {
        id: 2,
        search_term: payload.search_term,
        stream_type: payload.stream_type,
        description: payload.description ?? null,
        is_active: payload.is_active,
        created_at: '2026-03-22T00:00:00Z',
        updated_at: '2026-03-22T00:00:00Z',
      };
      queries.push(item);
      return item as any;
    });
    vi.spyOn(apiService, 'updateQuery').mockImplementation(async (id: number, payload: any) => {
      const index = queries.findIndex((q) => q.id === id);
      queries[index] = { ...queries[index], ...payload };
      return queries[index] as any;
    });
    vi.spyOn(apiService, 'deleteQuery').mockImplementation(async (id: number) => {
      const index = queries.findIndex((q) => q.id === id);
      if (index >= 0) {
        queries.splice(index, 1);
      }
    });

    vi.spyOn(window, 'confirm').mockReturnValue(true);

    const user = userEvent.setup();
    render(<Settings />);

    await waitFor(() => {
      expect(screen.getByText(/initial term/i)).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(/search query/i), ' New query');
    await user.type(screen.getByLabelText(/description/i), ' Optional description');
    await user.click(screen.getByRole('button', { name: /add query/i }));

    await waitFor(() => {
      expect(screen.getByText(/new query/i)).toBeInTheDocument();
    });

    const toggle = screen.getByLabelText('toggle-1');
    await user.click(toggle);

    expect(apiService.updateQuery).toHaveBeenCalledWith(1, { is_active: false });

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.queryByText(/initial term/i)).not.toBeInTheDocument();
    });
  });
});
