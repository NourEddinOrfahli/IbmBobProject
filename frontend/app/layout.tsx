import type { Metadata } from 'next';
import './globals.css';
import SpaceNav from '@/components/navigation/SpaceNav';

export const metadata: Metadata = {
  title: 'SPACE INTERPRETER — مترجم الفضاء',
  description:
    'منصة فلكية عربية مدعومة بالذكاء الاصطناعي. افهم الكون، حلل صور الفضاء، واستكشف قصص ناسا بالعربية.',
  metadataBase: new URL('http://localhost:3000'),
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ar" dir="rtl">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#050712" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <SpaceNav />
        <main style={{ minHeight: 'calc(100vh - 56px)' }}>
          {children}
        </main>
      </body>
    </html>
  );
}
