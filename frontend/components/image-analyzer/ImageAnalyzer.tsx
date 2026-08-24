'use client';

import { useRef, useState } from 'react';
import { analyzeImage, APIClientError } from '@/lib/api';
import type { ImageAnalysisResult } from '@/lib/types';
import ConfidenceBadge from '@/components/ui/ConfidenceBadge';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type AnalyzerState =
  | { phase: 'idle' }
  | { phase: 'preview'; file: File; previewUrl: string }
  | { phase: 'loading'; file: File; previewUrl: string }
  | { phase: 'result'; file: File; previewUrl: string; result: ImageAnalysisResult }
  | { phase: 'error'; file: File | null; previewUrl: string | null; message: string };

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_SIZE_MB = 5;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

function validateFile(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) {
    return 'نوع الملف غير مدعوم. يُرجى اختيار صورة JPEG أو PNG أو WEBP.';
  }
  if (file.size > MAX_SIZE_BYTES) {
    return `حجم الصورة يتجاوز ${MAX_SIZE_MB} ميغابايت. يُرجى اختيار صورة أصغر.`;
  }
  if (file.size === 0) {
    return 'الملف المختار فارغ.';
  }
  return null;
}

// ---------------------------------------------------------------------------
// Analysis Result — scientific layout
// ---------------------------------------------------------------------------

function AnalysisResult({ result }: { result: ImageAnalysisResult }) {
  if (!result.is_space_related) {
    return (
      <div
        lang="ar"
        dir="rtl"
        style={{
          background: 'rgba(255,45,154,0.05)',
          border: '1px solid rgba(255,45,154,0.2)',
          borderRadius: '12px',
          padding: '20px 24px',
          color: 'var(--text-muted)',
          fontSize: '15px',
          lineHeight: 1.9,
        }}
      >
        <span aria-hidden="true" style={{ marginLeft: '8px', color: 'var(--pulsar-pink)' }}>⚠</span>
        {result.summary || 'يبدو أن هذه الصورة لا تتعلق بالفضاء. جرّب صورة أخرى.'}
      </div>
    );
  }

  return (
    <div lang="ar" dir="rtl" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Title + Confidence */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        paddingBottom: '16px',
        borderBottom: '1px solid var(--border)',
      }}>
        <h2
          style={{
            fontSize: 'clamp(18px, 3vw, 24px)',
            fontWeight: 700,
            color: 'var(--stellar-white)',
            margin: 0,
            lineHeight: 1.4,
            flex: 1,
          }}
        >
          {result.title}
        </h2>
        <ConfidenceBadge confidence={result.confidence} />
      </div>

      {/* Summary */}
      <p style={{
        color: 'var(--text-muted)',
        fontSize: '15px',
        lineHeight: 2,
        margin: 0,
        padding: '16px 20px',
        background: 'rgba(0,217,255,0.03)',
        border: '1px solid rgba(0,217,255,0.1)',
        borderRadius: '10px',
        borderRight: '3px solid rgba(0,217,255,0.4)',
      }}>
        {result.summary}
      </p>

      {/* Observations */}
      {result.observations.length > 0 && (
        <section aria-label="ما الذي نراه">
          <h3 style={sectionHeadingStyle}>ما الذي نراه؟</h3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {result.observations.map((obs, i) => (
              <li
                key={i}
                style={{
                  display: 'flex',
                  gap: '12px',
                  color: 'var(--text-muted)',
                  fontSize: '14px',
                  lineHeight: 1.8,
                  padding: '6px 0',
                }}
              >
                <span
                  aria-hidden="true"
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: 'var(--pulsar-blue)',
                    flexShrink: 0,
                    marginTop: '8px',
                    boxShadow: '0 0 4px rgba(0,217,255,0.5)',
                  }}
                />
                <span>{obs}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Scientific explanation */}
      <section aria-label="التفسير العلمي">
        <h3 style={sectionHeadingStyle}>التفسير العلمي</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: 2, margin: 0 }}>
          {result.scientific_explanation}
        </p>
      </section>

      {/* Question answer */}
      {result.question_answer && result.question_answer.trim() && (
        <section aria-label="إجابة سؤالك" style={{
          padding: '16px 20px',
          background: 'rgba(122,44,255,0.04)',
          border: '1px solid rgba(122,44,255,0.15)',
          borderRadius: '10px',
          borderRight: '3px solid rgba(122,44,255,0.5)',
        }}>
          <h3 style={{ ...sectionHeadingStyle, color: 'var(--plasma-violet)', marginBottom: '8px' }}>إجابة سؤالك</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: 2, margin: 0 }}>
            {result.question_answer}
          </p>
        </section>
      )}

      {/* Story */}
      {result.story && result.story.trim() && (
        <section aria-label="القصة">
          <h3 style={sectionHeadingStyle}>القصة</h3>
          <p
            style={{
              color: 'var(--text-muted)',
              fontSize: '14px',
              lineHeight: 2,
              margin: 0,
              borderRight: '3px solid rgba(0,217,255,0.3)',
              paddingRight: '16px',
            }}
          >
            {result.story}
          </p>
        </section>
      )}
    </div>
  );
}

const sectionHeadingStyle: React.CSSProperties = {
  fontSize: '10px',
  fontWeight: 700,
  color: 'var(--pulsar-blue)',
  marginBottom: '10px',
  marginTop: 0,
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  opacity: 0.9,
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ImageAnalyzer() {
  const [state, setState] = useState<AnalyzerState>({ phase: 'idle' });
  const [question, setQuestion] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const error = validateFile(file);
    if (error) {
      setState({ phase: 'error', file: null, previewUrl: null, message: error });
      return;
    }

    const previewUrl = URL.createObjectURL(file);
    setState({ phase: 'preview', file, previewUrl });
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;

    const error = validateFile(file);
    if (error) {
      setState({ phase: 'error', file: null, previewUrl: null, message: error });
      return;
    }

    const previewUrl = URL.createObjectURL(file);
    setState({ phase: 'preview', file, previewUrl });
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave() {
    setIsDragOver(false);
  }

  function handleReset() {
    if (state.phase !== 'idle' && (state as { previewUrl?: string | null }).previewUrl) {
      URL.revokeObjectURL((state as { previewUrl: string }).previewUrl);
    }
    setState({ phase: 'idle' });
    setQuestion('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function handleSubmit() {
    if (state.phase !== 'preview' && state.phase !== 'result') return;
    const currentState = state as { file: File; previewUrl: string };

    setState({ phase: 'loading', file: currentState.file, previewUrl: currentState.previewUrl });

    try {
      const result = await analyzeImage(currentState.file, question || undefined);
      setState({
        phase: 'result',
        file: currentState.file,
        previewUrl: currentState.previewUrl,
        result,
      });
    } catch (err) {
      const message =
        err instanceof APIClientError
          ? err.message
          : 'حدث خطأ غير متوقع. يرجى المحاولة مجدداً.';
      setState({
        phase: 'error',
        file: currentState.file,
        previewUrl: currentState.previewUrl,
        message,
      });
    }
  }

  const isLoading = state.phase === 'loading';
  const hasFile = state.phase === 'preview' || state.phase === 'loading' || state.phase === 'result';
  const previewUrl = hasFile ? (state as { previewUrl: string }).previewUrl : null;

  return (
    <div lang="ar" dir="rtl">

      {/* Visually hidden title for accessibility and tests */}
      <h2 style={{ position: 'absolute', width: '1px', height: '1px', padding: 0, margin: '-1px', overflow: 'hidden', clip: 'rect(0,0,0,0)', whiteSpace: 'nowrap', borderWidth: 0 }}>
        حلّل صورة فضائية
      </h2>

      {/* Drop zone / file picker — idle state */}
      {!hasFile && (
        <div
          role="button"
          tabIndex={0}
          aria-label="انقر أو اسحب صورة هنا لتحليلها"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
          className={`pulsar-dropzone ${isDragOver ? 'drag-over' : ''}`}
          style={{
            padding: 'clamp(40px, 8vw, 72px) 24px',
            textAlign: 'center',
            marginBottom: '20px',
          }}
          data-testid="drop-zone"
        >
          {/* Large pulsar icon */}
          <div
            aria-hidden="true"
            style={{
              position: 'relative',
              width: '64px',
              height: '64px',
              margin: '0 auto 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div style={{
              position: 'absolute',
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              border: '1px solid rgba(0,217,255,0.2)',
              animation: 'pulsarRing 3s ease-in-out infinite',
            }} />
            <div style={{
              position: 'absolute',
              width: '44px',
              height: '44px',
              borderRadius: '50%',
              border: '1px solid rgba(0,217,255,0.12)',
              animation: 'pulsarRing 3s ease-in-out 0.8s infinite',
            }} />
            <span style={{ fontSize: '26px', zIndex: 1 }}>📷</span>
          </div>

          <div style={{ fontWeight: 700, fontSize: '17px', color: 'var(--stellar-white)', marginBottom: '8px' }}>
            اسحب الصورة إلى هنا
          </div>
          <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '6px' }}>
            أو اختر صورة من جهازك
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-faint)', marginTop: '12px' }}>
            JPEG · PNG · WEBP · الحد الأقصى {MAX_SIZE_MB} ميغابايت
          </div>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        style={{ display: 'none' }}
        onChange={handleFileChange}
        data-testid="file-input"
        aria-label="اختر صورة فضائية للتحليل"
      />

      {/* Image preview */}
      {previewUrl && (
        <div style={{ marginBottom: '20px', position: 'relative' }}>
          {/* Scanning overlay during loading */}
          {isLoading && (
            <div
              aria-hidden="true"
              style={{
                position: 'absolute',
                inset: 0,
                zIndex: 2,
                borderRadius: '12px',
                overflow: 'hidden',
                pointerEvents: 'none',
              }}
            >
              {/* Scan line */}
              <div style={{
                position: 'absolute',
                width: '100%',
                height: '2px',
                background: 'linear-gradient(90deg, transparent, var(--pulsar-blue), transparent)',
                boxShadow: '0 0 8px rgba(0,217,255,0.8)',
                animation: 'pulsarScan 2s ease-in-out infinite',
                top: 0,
              }} />
              {/* Dim overlay */}
              <div style={{
                position: 'absolute',
                inset: 0,
                background: 'rgba(5,7,18,0.35)',
                borderRadius: '12px',
              }} />
            </div>
          )}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewUrl}
            alt="معاينة الصورة المختارة"
            data-testid="image-preview"
            style={{
              width: '100%',
              maxHeight: '360px',
              objectFit: 'contain',
              borderRadius: '12px',
              border: `1px solid ${isLoading ? 'rgba(0,217,255,0.3)' : 'var(--border)'}`,
              background: 'rgba(255,255,255,0.02)',
              display: 'block',
              transition: 'border-color 0.3s',
            }}
          />
          {!isLoading && (
            <button
              onClick={handleReset}
              aria-label="إزالة الصورة"
              style={{
                position: 'absolute',
                top: '10px',
                left: '10px',
                background: 'rgba(5,7,18,0.85)',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: '8px',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '12px',
                padding: '5px 12px',
                backdropFilter: 'blur(8px)',
              }}
            >
              ✕ تغيير
            </button>
          )}
        </div>
      )}

      {/* Question input — always in DOM; only visible when there is a file */}
      {(hasFile || state.phase === 'idle') && (
        <div style={{ marginBottom: '16px' }}>
          <label
            htmlFor="vision-question"
            style={{
              display: 'block',
              fontSize: '12px',
              color: 'var(--text-muted)',
              marginBottom: '8px',
              fontWeight: 600,
              letterSpacing: '0.04em',
            }}
          >
            ماذا تريد أن تعرف؟{' '}
            <span style={{ color: 'var(--text-faint)', fontWeight: 400 }}>(اختياري)</span>
          </label>
          <input
            id="vision-question"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="مثال: هل هذا كوكب أم نجم؟ اشرحلي."
            maxLength={400}
            disabled={isLoading}
            data-testid="question-input"
            style={{
              width: '100%',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--border)',
              borderRadius: '10px',
              padding: '11px 14px',
              color: 'var(--text-primary)',
              fontSize: '14px',
              outline: 'none',
              boxSizing: 'border-box',
              direction: 'rtl',
              opacity: isLoading ? 0.5 : 1,
              transition: 'border-color 0.15s',
            }}
          />
        </div>
      )}

      {/* Submit / Analyze button */}
      {hasFile && state.phase !== 'loading' && (
        <button
          onClick={handleSubmit}
          disabled={isLoading}
          data-testid="submit-button"
          className="btn-pulsar"
          style={{
            width: '100%',
            padding: '14px',
            fontSize: '15px',
            marginBottom: '20px',
          }}
        >
          تحليل الصورة بالذكاء الاصطناعي
        </button>
      )}

      {/* Loading state — pulsar scan */}
      {isLoading && (
        <div
          role="status"
          aria-live="polite"
          data-testid="loading-indicator"
          style={{
            textAlign: 'center',
            padding: '24px',
            color: 'var(--text-muted)',
            fontSize: '14px',
          }}
        >
          {/* Pulsar loading animation */}
          <div
            aria-hidden="true"
            style={{
              position: 'relative',
              width: '40px',
              height: '40px',
              margin: '0 auto 14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div style={{
              position: 'absolute',
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              border: '2px solid transparent',
              borderTopColor: 'var(--pulsar-blue)',
              borderRightColor: 'rgba(0,217,255,0.3)',
              animation: 'spinSlow 1.2s linear infinite',
            }} />
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: 'var(--pulsar-blue)',
              boxShadow: '0 0 8px rgba(0,217,255,0.8)',
              animation: 'pulsarCore 1.4s ease-in-out infinite',
            }} />
          </div>
          جاري تحليل الصورة…
          <style>{`
            @keyframes pulsarScan {
              0%   { top: 0; opacity: 0; }
              10%  { opacity: 1; }
              90%  { opacity: 1; }
              100% { top: 100%; opacity: 0; }
            }
          `}</style>
        </div>
      )}

      {/* Error state */}
      {state.phase === 'error' && (
        <div
          role="alert"
          data-testid="error-message"
          style={{
            background: 'rgba(255,45,154,0.05)',
            border: '1px solid rgba(255,45,154,0.25)',
            borderRadius: '10px',
            padding: '14px 18px',
            color: 'var(--accent-red)',
            fontSize: '14px',
            lineHeight: 1.7,
            marginBottom: '12px',
          }}
        >
          <span aria-hidden="true" style={{ marginLeft: '8px' }}>⚠</span>
          {state.message}
        </div>
      )}

      {/* Analysis result */}
      {state.phase === 'result' && (
        <div
          data-testid="analysis-result"
          className="animate-fade-in"
          style={{
            borderTop: '1px solid var(--border)',
            paddingTop: '24px',
            marginTop: '8px',
          }}
        >
          <AnalysisResult result={state.result} />
        </div>
      )}

      {/* Re-analyse after result */}
      {state.phase === 'result' && (
        <button
          onClick={handleReset}
          className="btn-secondary"
          style={{
            marginTop: '24px',
            padding: '9px 20px',
            fontSize: '13px',
          }}
          data-testid="reset-button"
        >
          ↩ تحليل صورة أخرى
        </button>
      )}
    </div>
  );
}
