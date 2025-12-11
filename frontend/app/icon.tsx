import { ImageResponse } from 'next/og';

export const size = {
  width: 32,
  height: 32,
};

export const contentType = 'image/png';

export default async function Icon() {
  try {
    return new ImageResponse(
      (
        <div
          style={{
            fontSize: 20,
            background: 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)',
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            borderRadius: '8px',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '24px',
              height: '24px',
            }}
          >
            {/* Memory chip icon */}
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M6 2c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2H6zm0 2h12v16H6V4zm2 2v12h8V6H8zm2 2h4v2h-4V8zm0 4h4v2h-4v-2z"/>
            </svg>
          </div>
        </div>
      ),
      {
        ...size,
      }
    );
  } catch {
    // Fallback: return a simple response
    return new Response('', { status: 200 });
  }
}