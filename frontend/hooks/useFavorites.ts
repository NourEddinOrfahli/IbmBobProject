'use client';

import { useState, useEffect, useCallback } from 'react';
import type { StoryCard } from '@/lib/types';

const STORAGE_KEY = 'space_interpreter_favorites';

export interface UseFavoritesResult {
  favorites: StoryCard[];
  isFavorite: (id: string) => boolean;
  toggleFavorite: (story: StoryCard) => void;
  clearFavorites: () => void;
}

function loadFromStorage(): StoryCard[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as StoryCard[];
  } catch {
    return [];
  }
}

function saveToStorage(favorites: StoryCard[]): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
  } catch {
    // Storage quota exceeded or unavailable — fail silently
  }
}

export function useFavorites(): UseFavoritesResult {
  const [favorites, setFavorites] = useState<StoryCard[]>([]);

  // Hydrate from localStorage after mount
  useEffect(() => {
    setFavorites(loadFromStorage());
  }, []);

  const isFavorite = useCallback(
    (id: string) => favorites.some((f) => f.id === id),
    [favorites],
  );

  const toggleFavorite = useCallback((story: StoryCard) => {
    setFavorites((prev) => {
      const exists = prev.some((f) => f.id === story.id);
      const updated = exists
        ? prev.filter((f) => f.id !== story.id)
        : [story, ...prev];
      saveToStorage(updated);
      return updated;
    });
  }, []);

  const clearFavorites = useCallback(() => {
    setFavorites([]);
    saveToStorage([]);
  }, []);

  return { favorites, isFavorite, toggleFavorite, clearFavorites };
}
