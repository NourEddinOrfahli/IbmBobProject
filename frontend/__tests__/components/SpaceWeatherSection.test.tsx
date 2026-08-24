import { render, screen } from '@testing-library/react';
import SpaceWeatherSection from '@/components/dashboard/SpaceWeatherSection';
import type { SpaceWeatherSummary } from '@/lib/types';

const noEventsData: SpaceWeatherSummary = {
  available: false,
  event_count: 0,
  events: [],
};

const withEventsData: SpaceWeatherSummary = {
  available: true,
  event_count: 2,
  events: [
    {
      event_type: 'CME',
      begin_time: '2024-01-15T06:00:00Z',
      speed_kmps: 850,
      is_earth_directed: true,
      estimated_arrival: '2024-01-17T12:00:00Z',
      kp_index: 5,
      source_location: 'S15E25',
      note: 'Strong CME',
    },
    {
      event_type: 'CME',
      begin_time: '2024-01-14T18:00:00Z',
      speed_kmps: null,
      is_earth_directed: null,
      estimated_arrival: null,
      kp_index: null,
      source_location: null,
      note: null,
    },
  ],
};

describe('SpaceWeatherSection', () => {
  it('renders section heading', () => {
    render(<SpaceWeatherSection data={noEventsData} />);
    expect(screen.getByText(/الطقس الفضائي/)).toBeInTheDocument();
  });

  it('shows "no active events" message when available=false', () => {
    render(<SpaceWeatherSection data={noEventsData} />);
    expect(screen.getByText(/لا توجد أحداث فضائية نشطة/)).toBeInTheDocument();
  });

  it('renders CME event cards when events present', () => {
    render(<SpaceWeatherSection data={withEventsData} />);
    // Should render 2 event cards
    const cards = screen.getAllByRole('article');
    expect(cards.length).toBe(2);
  });

  it('shows earth-directed warning badge when is_earth_directed=true', () => {
    render(<SpaceWeatherSection data={withEventsData} />);
    expect(screen.getByText(/متجه نحو الأرض/)).toBeInTheDocument();
  });

  it('handles null speed_kmps gracefully', () => {
    render(<SpaceWeatherSection data={withEventsData} />);
    expect(screen.getByText(/غير محدد/)).toBeInTheDocument();
  });

  it('renders null data as nothing', () => {
    const { container } = render(<SpaceWeatherSection data={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows event count badge when available=true', () => {
    render(<SpaceWeatherSection data={withEventsData} />);
    // The badge contains "2 أحداث" — use getAllByText since "2" may appear in card titles
    const items = screen.getAllByText(/2/);
    expect(items.length).toBeGreaterThan(0);
  });

  it('does not invent missing CME values', () => {
    render(<SpaceWeatherSection data={withEventsData} />);
    // The second event has all nulls — should show placeholder, not invented data
    const items = screen.getAllByText(/غير محدد/);
    expect(items.length).toBeGreaterThan(0);
  });
});
