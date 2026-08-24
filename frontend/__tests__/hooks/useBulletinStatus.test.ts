import { renderHook, waitFor } from '@testing-library/react';
import { useBulletinStatus } from '@/hooks/useBulletinStatus';

// Preserve real APIClientError class so instanceof checks in the hook work
jest.mock('@/lib/api', () => {
  const actual = jest.requireActual('@/lib/api');
  return {
    ...actual,
    fetchStatus: jest.fn(),
  };
});

import { fetchStatus, APIClientError } from '@/lib/api';
const mockFetchStatus = fetchStatus as jest.MockedFunction<typeof fetchStatus>;

const mockStatus = {
  scheduler: {
    enabled: false,
    last_run: null,
    last_success: null,
    apod_date: null,
    status: null,
  },
  latest_bulletin: null,
};

describe('useBulletinStatus', () => {
  beforeEach(() => mockFetchStatus.mockReset());

  it('starts with loading=true', () => {
    mockFetchStatus.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useBulletinStatus());
    expect(result.current.loading).toBe(true);
    expect(result.current.status).toBeNull();
  });

  it('returns status data on success', async () => {
    mockFetchStatus.mockResolvedValueOnce(mockStatus);
    const { result } = renderHook(() => useBulletinStatus());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.status).toEqual(mockStatus);
    expect(result.current.error).toBeNull();
  });

  it('sets error gracefully on failure without throwing', async () => {
    mockFetchStatus.mockRejectedValueOnce(
      new APIClientError('NETWORK_ERROR', 'لا يمكن الاتصال'),
    );
    const { result } = renderHook(() => useBulletinStatus());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.status).toBeNull();
    expect(result.current.error).toBe('لا يمكن الاتصال');
    // Crucially: loading is false, not stuck
    expect(result.current.loading).toBe(false);
  });
});
