import { ImageResponse } from 'next/og';

// Edge runtime is automatically used for ImageResponse from next/og

export const size = {
  width: 180,
  height: 180,
};

export const contentType = 'image/png';

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          fontSize: 72,
          background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          borderRadius: '32px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '120px',
            height: '120px',
          }}
        >
          {/* Memory chip icon */}
          <svg
            width="80"
            height="80"
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
}