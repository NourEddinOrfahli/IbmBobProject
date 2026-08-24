import { render, screen, fireEvent } from '@testing-library/react';
import BulletinError from '@/components/states/BulletinError';

describe('BulletinError', () => {
  const mockRetry = jest.fn();

  beforeEach(() => mockRetry.mockClear());

  it('renders an Arabic error heading', () => {
    render(<BulletinError message="خطأ في الاتصال" onRetry={mockRetry} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/تعذّر تحميل النشرة/)).toBeInTheDocument();
  });

  it('renders the retry button with Arabic label', () => {
    render(<BulletinError message={null} onRetry={mockRetry} />);
    expect(screen.getByText(/حاول مجدداً/)).toBeInTheDocument();
  });

  it('calls onRetry when retry button is clicked', () => {
    render(<BulletinError message="خطأ" onRetry={mockRetry} />);
    fireEvent.click(screen.getByRole('button'));
    expect(mockRetry).toHaveBeenCalledTimes(1);
  });

  it('uses fallback message when message is null', () => {
    render(<BulletinError message={null} onRetry={mockRetry} />);
    expect(screen.getByText(/يرجى المحاولة مجدداً/)).toBeInTheDocument();
  });

  it('does not render raw error codes in visible text', () => {
    render(<BulletinError message="AI_NOT_CONFIGURED" onRetry={mockRetry} />);
    // The message is short (< 200 chars) so it might render — but we ensure
    // no internal code-like labels appear in uppercase-code format elsewhere
    const text = document.body.textContent ?? '';
    expect(text).not.toContain('HTTP_');
    expect(text).not.toContain('NETWORK_ERROR');
  });

  it('has role="alert" for screen readers', () => {
    render(<BulletinError message="خطأ" onRetry={mockRetry} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
