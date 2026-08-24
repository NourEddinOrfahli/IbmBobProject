import { render, screen } from '@testing-library/react';
import BulletinSkeleton from '@/components/states/BulletinSkeleton';

describe('BulletinSkeleton', () => {
  it('renders without crashing', () => {
    render(<BulletinSkeleton />);
  });

  it('has aria-busy="true"', () => {
    render(<BulletinSkeleton />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true');
  });

  it('contains Arabic loading label', () => {
    render(<BulletinSkeleton />);
    expect(screen.getByLabelText(/جاري تحميل/)).toBeInTheDocument();
  });

  it('renders skeleton pulse elements', () => {
    render(<BulletinSkeleton />);
    const skeletons = document.querySelectorAll('.skeleton');
    expect(skeletons.length).toBeGreaterThan(4);
  });
});
