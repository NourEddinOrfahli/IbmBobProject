/**
 * Tests for the useFavorites hook.
 *
 * Covers:
 * - Initial state empty
 * - Toggle favorite adds item
 * - Toggle again removes item
 * - isFavorite returns correct value
 * - clearFavorites empties list
 */

import { renderHook, act } from '@testing-library/react';
import { useFavorites } from '@/hooks/useFavorites';
import type { StoryCard } from '@/lib/types';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

function makeStory(id: string): StoryCard {
  return {
    id,
    date: `2024-01-${id}`,
    title: `Story ${id}`,
    summary: `Summary ${id}`,
    image_url: null,
    hd_image_url: null,
    media_type: 'image',
    copyright: null,
    source: 'NASA APOD',
  };
}

describe('useFavorites', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('starts with empty favorites', () => {
    const { result } = renderHook(() => useFavorites());
    expect(result.current.favorites).toHaveLength(0);
  });

  it('toggleFavorite adds a story', () => {
    const { result } = renderHook(() => useFavorites());
    const story = makeStory('01');

    act(() => {
      result.current.toggleFavorite(story);
    });

    expect(result.current.favorites).toHaveLength(1);
    expect(result.current.favorites[0].id).toBe('01');
  });

  it('toggleFavorite removes an existing story', () => {
    const { result } = renderHook(() => useFavorites());
    const story = makeStory('01');

    act(() => result.current.toggleFavorite(story));
    act(() => result.current.toggleFavorite(story));

    expect(result.current.favorites).toHaveLength(0);
  });

  it('isFavorite returns true for saved story', () => {
    const { result } = renderHook(() => useFavorites());
    const story = makeStory('01');

    act(() => result.current.toggleFavorite(story));

    expect(result.current.isFavorite('01')).toBe(true);
  });

  it('isFavorite returns false for unsaved story', () => {
    const { result } = renderHook(() => useFavorites());
    expect(result.current.isFavorite('99')).toBe(false);
  });

  it('clearFavorites empties the list', () => {
    const { result } = renderHook(() => useFavorites());
    const story1 = makeStory('01');
    const story2 = makeStory('02');

    act(() => {
      result.current.toggleFavorite(story1);
      result.current.toggleFavorite(story2);
    });

    expect(result.current.favorites).toHaveLength(2);

    act(() => result.current.clearFavorites());

    expect(result.current.favorites).toHaveLength(0);
  });

  it('persists favorites across hook instances (localStorage)', () => {
    const story = makeStory('01');

    const { result: r1 } = renderHook(() => useFavorites());
    act(() => r1.current.toggleFavorite(story));

    // Simulate page reload by re-rendering hook
    const { result: r2 } = renderHook(() => useFavorites());
    expect(r2.current.isFavorite('01')).toBe(true);
  });
});
