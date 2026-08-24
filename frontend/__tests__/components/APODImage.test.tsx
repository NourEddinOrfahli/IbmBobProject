import { render, screen } from '@testing-library/react';
import APODImage from '@/components/ui/APODImage';
import type { SourceData } from '@/lib/types';

function makeSource(overrides: Partial<SourceData> = {}): SourceData {
  return {
    source: 'NASA APOD',
    date: '2024-01-15',
    title: 'Test APOD',
    media_type: 'image',
    image_url: 'https://apod.nasa.gov/apod/image/test.jpg',
    hd_image_url: null,
    copyright: null,
    ...overrides,
  };
}

describe('APODImage', () => {
  it('renders an img when media_type=image and image_url is present', () => {
    render(<APODImage sourceData={makeSource()} />);
    const img = screen.getByRole('img', { hidden: true }) as HTMLImageElement | null;
    // The component may use <img> tag
    const images = document.querySelectorAll('img');
    expect(images.length).toBeGreaterThan(0);
    expect(images[0].src).toContain('test.jpg');
  });

  it('renders nothing image-like when image_url is null', () => {
    render(<APODImage sourceData={makeSource({ image_url: null, hd_image_url: null })} />);
    const images = document.querySelectorAll('img');
    expect(images.length).toBe(0);
  });

  it('prefers hd_image_url when both are present', () => {
    render(
      <APODImage
        sourceData={makeSource({
          image_url: 'https://apod.nasa.gov/apod/image/std.jpg',
          hd_image_url: 'https://apod.nasa.gov/apod/image/hd.jpg',
        })}
      />,
    );
    const images = document.querySelectorAll('img');
    expect(images[0].src).toContain('hd.jpg');
  });

  it('shows video placeholder for media_type=video', () => {
    render(<APODImage sourceData={makeSource({ media_type: 'video', image_url: null })} />);
    const images = document.querySelectorAll('img');
    expect(images.length).toBe(0);
    // Should have an accessible label about video
    expect(document.body.textContent).toContain('فيديو');
  });

  it('shows fallback when media_type=image but image_url is empty string', () => {
    render(<APODImage sourceData={makeSource({ image_url: '', hd_image_url: '' })} />);
    const images = document.querySelectorAll('img');
    expect(images.length).toBe(0);
  });

  it('uses APOD title as alt text', () => {
    render(<APODImage sourceData={makeSource({ title: 'Pillars of Creation' })} />);
    const img = document.querySelector('img');
    expect(img?.alt).toContain('Pillars of Creation');
  });
});
