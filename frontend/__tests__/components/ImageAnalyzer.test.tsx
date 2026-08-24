/**
 * Tests for the ImageAnalyzer component.
 *
 * Covers:
 * - Image selection via file input
 * - Image preview rendering
 * - Question input interaction
 * - Submit/loading state
 * - Successful result rendering
 * - Error rendering
 * - No-image validation (submit disabled)
 * - Drop zone rendered initially
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImageAnalyzer from '@/components/image-analyzer/ImageAnalyzer';
import { analyzeImage, APIClientError } from '@/lib/api';

// ---------------------------------------------------------------------------
// Mock the API
// ---------------------------------------------------------------------------

jest.mock('@/lib/api', () => ({
  analyzeImage: jest.fn(),
  APIClientError: class APIClientError extends Error {
    code: string;
    constructor(code: string, message: string) {
      super(message);
      this.code = code;
      this.name = 'APIClientError';
    }
  },
}));

const mockAnalyzeImage = analyzeImage as jest.MockedFunction<typeof analyzeImage>;

// ---------------------------------------------------------------------------
// Mock URL.createObjectURL / URL.revokeObjectURL
// ---------------------------------------------------------------------------

const mockObjectUrl = 'blob:http://localhost/mock-image-url';
global.URL.createObjectURL = jest.fn(() => mockObjectUrl);
global.URL.revokeObjectURL = jest.fn();

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeFile(name = 'space.jpg', type = 'image/jpeg', size = 1024): File {
  const content = new Uint8Array(size).fill(0);
  return new File([content], name, { type });
}

function makeAnalysisResult(overrides = {}) {
  return {
    title: 'سديم جميل في الفضاء',
    summary: 'صورة لسديم بعيد.',
    observations: ['سحاب غازي', 'نجوم مضيئة'],
    scientific_explanation: 'يُرجَّح أن هذا سديم انبعاثي.',
    confidence: 'high',
    story: 'قصة قصيرة عن الفضاء.',
    question_answer: '',
    is_space_related: true,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ImageAnalyzer', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── Initial render ────────────────────────────────────────────────────────

  it('renders the component title', () => {
    render(<ImageAnalyzer />);
    expect(screen.getByText(/حلّل صورة فضائية/)).toBeInTheDocument();
  });

  it('renders the drop zone initially', () => {
    render(<ImageAnalyzer />);
    expect(screen.getByTestId('drop-zone')).toBeInTheDocument();
  });

  it('renders the file input', () => {
    render(<ImageAnalyzer />);
    expect(screen.getByTestId('file-input')).toBeInTheDocument();
  });

  it('renders the question input', () => {
    render(<ImageAnalyzer />);
    expect(screen.getByTestId('question-input')).toBeInTheDocument();
  });

  it('does not show submit button before file is selected', () => {
    render(<ImageAnalyzer />);
    expect(screen.queryByTestId('submit-button')).not.toBeInTheDocument();
  });

  // ── File selection ────────────────────────────────────────────────────────

  it('shows image preview after file selection', async () => {
    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const file = makeFile();

    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } });
    });

    expect(screen.getByTestId('image-preview')).toBeInTheDocument();
    expect((screen.getByTestId('image-preview') as HTMLImageElement).src).toContain(
      'mock-image-url',
    );
  });

  it('shows submit button after file selection', async () => {
    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');
    const file = makeFile();

    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } });
    });

    expect(screen.getByTestId('submit-button')).toBeInTheDocument();
  });

  it('hides drop zone after file selection', async () => {
    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');
    const file = makeFile();

    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } });
    });

    expect(screen.queryByTestId('drop-zone')).not.toBeInTheDocument();
  });

  it('shows error for unsupported file type', async () => {
    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');
    const file = makeFile('document.pdf', 'application/pdf');

    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } });
    });

    expect(screen.getByTestId('error-message')).toBeInTheDocument();
    expect(screen.getByTestId('error-message').textContent).toContain('JPEG');
  });

  it('shows error for oversized file', async () => {
    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');
    // 6 MB — over the 5 MB limit
    const bigFile = makeFile('big.jpg', 'image/jpeg', 6 * 1024 * 1024);

    await act(async () => {
      fireEvent.change(input, { target: { files: [bigFile] } });
    });

    expect(screen.getByTestId('error-message')).toBeInTheDocument();
    const msg = screen.getByTestId('error-message').textContent ?? '';
    expect(msg).toMatch(/ميغابايت/);
  });

  // ── Question input ────────────────────────────────────────────────────────

  it('accepts text in the question input', async () => {
    render(<ImageAnalyzer />);
    const qInput = screen.getByTestId('question-input') as HTMLInputElement;

    await act(async () => {
      fireEvent.change(qInput, { target: { value: 'ما هذا الكوكب؟' } });
    });

    expect(qInput.value).toBe('ما هذا الكوكب؟');
  });

  it('respects maxLength=400 on question input', () => {
    render(<ImageAnalyzer />);
    const qInput = screen.getByTestId('question-input') as HTMLInputElement;
    expect(qInput.maxLength).toBe(400);
  });

  // ── Submit / loading ──────────────────────────────────────────────────────

  it('shows loading indicator while analyzing', async () => {
    let resolveAnalysis!: (v: ReturnType<typeof makeAnalysisResult>) => void;
    mockAnalyzeImage.mockImplementationOnce(
      () => new Promise((res) => { resolveAnalysis = res; }),
    );

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();

    // Clean up
    act(() => {
      resolveAnalysis(makeAnalysisResult());
    });
  });

  it('hides submit button while loading', async () => {
    let resolveAnalysis!: (v: ReturnType<typeof makeAnalysisResult>) => void;
    mockAnalyzeImage.mockImplementationOnce(
      () => new Promise((res) => { resolveAnalysis = res; }),
    );

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    expect(screen.queryByTestId('submit-button')).not.toBeInTheDocument();

    act(() => {
      resolveAnalysis(makeAnalysisResult());
    });
  });

  it('passes question to analyzeImage when provided', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(makeAnalysisResult());

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');
    const qInput = screen.getByTestId('question-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.change(qInput, { target: { value: 'هل هذا نجم؟' } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(mockAnalyzeImage).toHaveBeenCalledWith(
        expect.any(File),
        'هل هذا نجم؟',
      );
    });
  });

  // ── Successful result rendering ───────────────────────────────────────────

  it('shows analysis result after successful submit', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(makeAnalysisResult());

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('analysis-result')).toBeInTheDocument();
    });
  });

  it('displays the result title', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(makeAnalysisResult());

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByText('سديم جميل في الفضاء')).toBeInTheDocument();
    });
  });

  it('displays observations in the result', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(makeAnalysisResult());

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByText('سحاب غازي')).toBeInTheDocument();
    });
  });

  it('displays question answer when present', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(
      makeAnalysisResult({ question_answer: 'هذا نجم نيوتروني.' }),
    );

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByText('هذا نجم نيوتروني.')).toBeInTheDocument();
    });
  });

  it('shows reset button after result', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(makeAnalysisResult());

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('reset-button')).toBeInTheDocument();
    });
  });

  it('resets to idle state when reset button clicked', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(makeAnalysisResult());

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('reset-button')).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('reset-button'));
    });

    expect(screen.getByTestId('drop-zone')).toBeInTheDocument();
    expect(screen.queryByTestId('analysis-result')).not.toBeInTheDocument();
  });

  // ── Non-space image ───────────────────────────────────────────────────────

  it('shows non-space message when is_space_related is false', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(
      makeAnalysisResult({ is_space_related: false, summary: 'هذه ليست صورة فضائية.' }),
    );

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('analysis-result')).toBeInTheDocument();
      const result = screen.getByTestId('analysis-result');
      expect(result.textContent).toContain('هذه ليست صورة فضائية.');
    });
  });

  // ── Error rendering ───────────────────────────────────────────────────────

  it('shows error message on API failure', async () => {
    const { APIClientError: LocalError } = jest.requireActual('@/lib/api') as typeof import('@/lib/api');
    mockAnalyzeImage.mockRejectedValueOnce(
      new (class extends Error {
        code = 'AI_TIMEOUT';
        constructor() { super('انتهت مهلة الذكاء الاصطناعي.'); this.name = 'APIClientError'; }
      })(),
    );

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });
  });

  it('shows generic error message on unexpected exception', async () => {
    mockAnalyzeImage.mockRejectedValueOnce(new Error('Unexpected internal error'));

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      const errorEl = screen.getByTestId('error-message');
      expect(errorEl).toBeInTheDocument();
      // Should show Arabic user-friendly message, not raw exception
      expect(errorEl.textContent).not.toContain('Unexpected internal error');
    });
  });
});
