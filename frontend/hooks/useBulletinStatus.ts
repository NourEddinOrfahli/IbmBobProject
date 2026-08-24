'use client';

import { useState, useEffect } from 'react';
import { fetchStatus, APIClientError } from '@/lib/api';
import type { StatusData } from '@/lib/types';

export interface UseBulletinStatusResult {
  status: StatusData | null;
  loading: boolean;
  error: string | null;
}

export function useBulletinStatus(): UseBulletinStatusResult {
  const [status, setStatus] = useState<StatusData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const data = await fetchStatus();
        if (!cancelled) {
          setStatus(data);
        }
      } catch (err) {
        if (!cancelled) {
          // Status endpoint failure is non-fatal — degrade gracefully
          if (err instanceof APIClientError) {
            setError(err.message);
          } else {
            setError('تعذّر تحميل حالة النشرة.');
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
  }, []);

  return { status, loading, error };
}
