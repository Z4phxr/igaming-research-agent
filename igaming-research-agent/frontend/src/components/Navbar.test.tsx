import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import Navbar from '@/components/Navbar';


describe('Navbar', () => {
  it('shows expected navigation links', () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: /home/i })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: /history/i })).toHaveAttribute('href', '/history');
    expect(screen.getByRole('link', { name: /settings/i })).toHaveAttribute('href', '/settings');
  });
});
