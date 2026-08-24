import { renderHook, waitFor, act } from '@testing-library/react';
import { useDailyNews } from '@/hooks/useDailyNews';

// Mock the api module but preserve the real APIClientError class
jest.mock('@/lib/api', () => {
  const actual = jest.requireActual('@/lib/api');
  return {
    ...actual,
    fetchDailyNews: jest.fn(),
  };
});

import { fetchDailyNews, APIClientError } from '@/lib/api';
const mockFetchDailyNews = fetchDailyNews as jest.MockedFunction<typeof fetchDailyNews>;

const mockStory = {
  title: 'عنوان تجريبي',
  summary: 'ملخص',
  scientific_explanation: 'تفسير',
  key_facts: ['حقيقة 1'],
  why_it_matters: 'يهم',
  story: 'قصة',
  source_data: {
    source: 'NASA APOD',
    date: '2024-01-15',
    title: 'Test',
    media_type: 'image' as const,
    image_url: null,
    hd_image_url: null,
    copyright: null,
  },
  confidence: 'high' as const,
  language: 'ar',
  space_weather: null,
};

describe('useDailyNews', () => {
  beforeEach(() => mockFetchDailyNews.mockReset());

  it('starts with loading=true', () => {
    mockFetchDailyNews.mockReturnValue(new Promise(() => {})); // never resolves
    const { result } = renderHook(() => useDailyNews());
    expect(result.current.loading).toBe(true);
    expect(result.current.story).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('returns story on success', async () => {
    mockFetchDailyNews.mockResolvedValueOnce(mockStory);
    const { result } = renderHook(() => useDailyNews());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.story).toEqual(mockStory);
    expect(result.current.error).toBeNull();
  });

  it('returns error string on APIClientError failure', async () => {
    mockFetchDailyNews.mockRejectedValueOnce(
      new APIClientError('AI_TIMEOUT', 'انتهت مهلة الذكاء الاصطناعي'),
    );
    const { result } = renderHook(() => useDailyNews());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.story).toBeNull();
    expect(result.current.error).toBe('انتهت مهلة الذكاء الاصطناعي');
  });

  it('returns generic error for non-APIClientError', async () => {
    mockFetchDailyNews.mockRejectedValueOnce(new TypeError('unexpected'));
    const { result } = renderHook(() => useDailyNews());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toContain('غير متوقع');
  });

  it('refetch re-calls fetchDailyNews', async () => {
    mockFetchDailyNews.mockResolvedValue(mockStory);
    const { result } = renderHook(() => useDailyNews());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(mockFetchDailyNews).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.refetch();
    });
    await waitFor(() => expect(mockFetchDailyNews).toHaveBeenCalledTimes(2));
  });
});
