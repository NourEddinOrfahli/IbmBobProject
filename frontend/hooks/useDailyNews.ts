'use client';

import { useState, useEffect, useCallback } from 'react';
import { fetchDailyNews, APIClientError } from '@/lib/api';
import type { SpaceStory } from '@/lib/types';

export interface UseDailyNewsResult {
  story: SpaceStory | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useDailyNews(): UseDailyNewsResult {
  const [story, setStory] = useState<SpaceStory | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [fetchKey, setFetchKey] = useState<number>(0);

  const refetch = useCallback(() => {
    setFetchKey((k) => k + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const data = await fetchDailyNews();
        if (!cancelled) {
          setStory(data);
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof APIClientError) {
            setError(err.message);
          } else {
            setError('حدث خطأ غير متوقع. يرجى المحاولة مجدداً.');
          }
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [fetchKey]);

  return { story, loading, error, refetch };
}
