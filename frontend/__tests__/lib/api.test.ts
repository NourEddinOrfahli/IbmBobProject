import { fetchDailyNews, fetchStatus, analyzeImage, APIClientError } from '@/lib/api';

// Mock global fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

function makeSuccessStory(overrides = {}) {
  return {
    success: true,
    data: {
      title: 'عنوان تجريبي',
      summary: 'ملخص تجريبي',
      scientific_explanation: 'تفسير علمي',
      key_facts: ['حقيقة 1', 'حقيقة 2'],
      why_it_matters: 'لماذا يهمنا',
      story: 'القصة الكاملة',
      source_data: {
        source: 'NASA APOD',
        date: '2024-01-15',
        title: 'Test APOD Title',
        media_type: 'image',
        image_url: 'https://apod.nasa.gov/apod/image/test.jpg',
        hd_image_url: 'https://apod.nasa.gov/apod/image/test_hd.jpg',
        copyright: null,
      },
      confidence: 'high',
      language: 'ar',
      space_weather: {
        available: false,
        event_count: 0,
        events: [],
      },
      ...overrides,
    },
  };
}

function makeErrorBody(code: string, message: string) {
  return { success: false, error: { code, message } };
}

beforeEach(() => {
  mockFetch.mockReset();
});

// ---------------------------------------------------------------------------
// fetchDailyNews
// ---------------------------------------------------------------------------

describe('fetchDailyNews', () => {
  it('returns SpaceStory on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeSuccessStory(),
    } as Response);

    const result = await fetchDailyNews();
    expect(result.title).toBe('عنوان تجريبي');
    expect(result.source_data.source).toBe('NASA APOD');
    expect(result.space_weather?.available).toBe(false);
  });

  it('throws APIClientError on success:false body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 502,
      json: async () => makeErrorBody('AI_TIMEOUT', 'AI timed out'),
    } as Response);

    const promise = fetchDailyNews();
    await expect(promise).rejects.toBeInstanceOf(APIClientError);
  });

  it('throws correct error code on error body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 502,
      json: async () => makeErrorBody('AI_TIMEOUT', 'AI timed out'),
    } as Response);

    await expect(fetchDailyNews()).rejects.toMatchObject({ code: 'AI_TIMEOUT' });
  });

  it('throws NETWORK_ERROR on fetch failure', async () => {
    mockFetch.mockRejectedValueOnce(new TypeError('network down'));

    await expect(fetchDailyNews()).rejects.toMatchObject({ code: 'NETWORK_ERROR' });
  });

  it('throws PARSE_ERROR when response is not JSON', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => { throw new SyntaxError('not json'); },
    } as unknown as Response);

    await expect(fetchDailyNews()).rejects.toBeInstanceOf(APIClientError);
  });

  it('uses correct endpoint URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeSuccessStory(),
    } as Response);

    await fetchDailyNews();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/daily-news'),
      expect.any(Object),
    );
  });
});

// ---------------------------------------------------------------------------
// fetchStatus
// ---------------------------------------------------------------------------

describe('fetchStatus', () => {
  it('returns StatusData on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: {
          scheduler: {
            enabled: false,
            last_run: null,
            last_success: null,
            apod_date: null,
            status: null,
          },
          latest_bulletin: null,
        },
      }),
    } as Response);

    const result = await fetchStatus();
    expect(result.scheduler.enabled).toBe(false);
    expect(result.latest_bulletin).toBeNull();
  });

  it('throws APIClientError on error response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => makeErrorBody('AI_NOT_CONFIGURED', 'Key missing'),
    } as Response);

    await expect(fetchStatus()).rejects.toBeInstanceOf(APIClientError);
  });
});

// ---------------------------------------------------------------------------
// analyzeImage
// ---------------------------------------------------------------------------

function makeAnalysisResult(overrides = {}) {
  return {
    success: true,
    data: {
      title: 'سديم رائع',
      summary: 'صورة لسديم.',
      observations: ['سحاب غازي'],
      scientific_explanation: 'يُرجَّح أن هذا سديم انبعاثي.',
      confidence: 'high',
      story: 'قصة قصيرة.',
      question_answer: '',
      is_space_related: true,
      ...overrides,
    },
  };
}

function makeImageFile(name = 'space.jpg', type = 'image/jpeg'): File {
  return new File([new Uint8Array(100)], name, { type });
}

describe('analyzeImage', () => {
  it('returns ImageAnalysisResult on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeAnalysisResult(),
    } as Response);

    const result = await analyzeImage(makeImageFile());
    expect(result.title).toBe('سديم رائع');
    expect(result.is_space_related).toBe(true);
  });

  it('passes question in FormData when provided', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeAnalysisResult(),
    } as Response);

    await analyzeImage(makeImageFile(), 'ما هذا؟');

    const [, options] = mockFetch.mock.calls[0];
    const body = (options as RequestInit).body as FormData;
    expect(body.get('question')).toBe('ما هذا؟');
  });

  it('does not include question in FormData when not provided', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeAnalysisResult(),
    } as Response);

    await analyzeImage(makeImageFile());

    const [, options] = mockFetch.mock.calls[0];
    const body = (options as RequestInit).body as FormData;
    expect(body.get('question')).toBeNull();
  });

  it('includes image file in FormData', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeAnalysisResult(),
    } as Response);

    const file = makeImageFile('nebula.jpg', 'image/jpeg');
    await analyzeImage(file);

    const [, options] = mockFetch.mock.calls[0];
    const body = (options as RequestInit).body as FormData;
    expect(body.get('image')).toBe(file);
  });

  it('uses correct endpoint URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeAnalysisResult(),
    } as Response);

    await analyzeImage(makeImageFile());
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/analyze-image'),
      expect.any(Object),
    );
  });

  it('uses POST method', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeAnalysisResult(),
    } as Response);

    await analyzeImage(makeImageFile());

    const [, options] = mockFetch.mock.calls[0];
    expect((options as RequestInit).method).toBe('POST');
  });

  it('throws APIClientError on error response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => makeErrorBody('UNSUPPORTED_IMAGE_TYPE', 'نوع الملف غير مدعوم.'),
    } as Response);

    await expect(analyzeImage(makeImageFile())).rejects.toBeInstanceOf(APIClientError);
  });

  it('throws correct error code on failure', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 413,
      json: async () => makeErrorBody('IMAGE_TOO_LARGE', 'الصورة كبيرة جداً.'),
    } as Response);

    await expect(analyzeImage(makeImageFile())).rejects.toMatchObject({
      code: 'IMAGE_TOO_LARGE',
    });
  });

  it('throws NETWORK_ERROR on fetch failure', async () => {
    mockFetch.mockRejectedValueOnce(new TypeError('network down'));

    await expect(analyzeImage(makeImageFile())).rejects.toMatchObject({
      code: 'NETWORK_ERROR',
    });
  });

  it('throws PARSE_ERROR on non-JSON response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => { throw new SyntaxError('not json'); },
    } as unknown as Response);

    await expect(analyzeImage(makeImageFile())).rejects.toBeInstanceOf(APIClientError);
  });
});
