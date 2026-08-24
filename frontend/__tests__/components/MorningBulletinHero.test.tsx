import { render, screen } from '@testing-library/react';
import MorningBulletinHero from '@/components/dashboard/MorningBulletinHero';
import type { SpaceStory } from '@/lib/types';

function makeStory(overrides: Partial<SpaceStory> = {}): SpaceStory {
  return {
    title: 'أعمدة الخلق',
    summary: 'ملخص النشرة الفضائية',
    scientific_explanation: 'تفسير علمي تفصيلي',
    key_facts: ['حقيقة 1'],
    why_it_matters: 'يهمنا لأن',
    story: 'قصة طويلة',
    source_data: {
      source: 'NASA APOD',
      date: '2024-01-15',
      title: 'Pillars of Creation',
      media_type: 'image',
      image_url: 'https://apod.nasa.gov/apod/image/test.jpg',
      hd_image_url: null,
      copyright: 'ESA/Hubble',
    },
    confidence: 'high',
    language: 'ar',
    space_weather: null,
    ...overrides,
  };
}

describe('MorningBulletinHero', () => {
  it('renders the Arabic title', () => {
    render(<MorningBulletinHero story={makeStory()} />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('أعمدة الخلق');
  });

  it('renders the summary', () => {
    render(<MorningBulletinHero story={makeStory()} />);
    expect(screen.getByText('ملخص النشرة الفضائية')).toBeInTheDocument();
  });

  it('renders "النشرة الفضائية الصباحية" label', () => {
    render(<MorningBulletinHero story={makeStory()} />);
    expect(screen.getByText(/النشرة الفضائية الصباحية/)).toBeInTheDocument();
  });

  it('renders APOD source attribution', () => {
    render(<MorningBulletinHero story={makeStory()} />);
    expect(screen.getByText(/NASA APOD/)).toBeInTheDocument();
  });

  it('renders original English APOD title', () => {
    render(<MorningBulletinHero story={makeStory()} />);
    expect(screen.getByText(/Pillars of Creation/)).toBeInTheDocument();
  });

  it('renders confidence badge', () => {
    render(<MorningBulletinHero story={makeStory()} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders copyright when present', () => {
    render(<MorningBulletinHero story={makeStory()} />);
    expect(screen.getByText(/ESA\/Hubble/)).toBeInTheDocument();
  });

  it('renders image when image_url is present', () => {
    render(<MorningBulletinHero story={makeStory()} />);
    const images = document.querySelectorAll('img');
    expect(images.length).toBeGreaterThan(0);
  });

  it('does not render img when image_url is null and media_type is image', () => {
    render(
      <MorningBulletinHero
        story={makeStory({
          source_data: {
            source: 'NASA APOD',
            date: '2024-01-15',
            title: 'Test',
            media_type: 'image',
            image_url: null,
            hd_image_url: null,
            copyright: null,
          },
        })}
      />,
    );
    const images = document.querySelectorAll('img');
    expect(images.length).toBe(0);
  });

  it('applies RTL direction', () => {
    render(<MorningBulletinHero story={makeStory()} />);
    const heading = screen.getByRole('heading', { level: 1 });
    // RTL must be applied to the heading itself or its container
    const parent = heading.closest('[dir="rtl"]');
    expect(parent).toBeTruthy();
  });
});
