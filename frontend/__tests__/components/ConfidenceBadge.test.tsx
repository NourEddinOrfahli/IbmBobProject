import { render, screen, fireEvent } from '@testing-library/react';
import ConfidenceBadge from '@/components/ui/ConfidenceBadge';

describe('ConfidenceBadge', () => {
  it('renders Arabic label for high confidence', () => {
    render(<ConfidenceBadge confidence="high" />);
    expect(screen.getByText('ثقة عالية')).toBeInTheDocument();
  });

  it('renders Arabic label for medium confidence', () => {
    render(<ConfidenceBadge confidence="medium" />);
    expect(screen.getByText('ثقة متوسطة')).toBeInTheDocument();
  });

  it('renders Arabic label for low confidence', () => {
    render(<ConfidenceBadge confidence="low" />);
    expect(screen.getByText('ثقة منخفضة')).toBeInTheDocument();
  });

  it('falls back to medium for unknown value', () => {
    render(<ConfidenceBadge confidence={'unknown' as 'high'} />);
    expect(screen.getByText('ثقة متوسطة')).toBeInTheDocument();
  });

  it('has accessible role="status"', () => {
    render(<ConfidenceBadge confidence="high" />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
