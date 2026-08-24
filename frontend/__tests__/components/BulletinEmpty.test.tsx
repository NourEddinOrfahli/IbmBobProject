import { render, screen } from '@testing-library/react';
import BulletinEmpty from '@/components/states/BulletinEmpty';

describe('BulletinEmpty', () => {
  it('renders the Arabic "being prepared" message', () => {
    render(<BulletinEmpty />);
    expect(screen.getByText(/قيد الإعداد/)).toBeInTheDocument();
  });

  it('does not contain any fake scientific content', () => {
    render(<BulletinEmpty />);
    const text = document.body.textContent ?? '';
    // No fake NASA data, coordinates, model responses
    expect(text).not.toMatch(/NASA APOD/i);
    expect(text).not.toMatch(/meta-llama/i);
    expect(text).not.toMatch(/openrouter/i);
  });
});
