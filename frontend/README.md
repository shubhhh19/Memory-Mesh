# memorymesh Frontend

This is the frontend web application for memorymesh, built with Next.js 15, React 19, and TypeScript.

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
Create a `.env.local` file in the `frontend` directory with:
```env
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# OAuth Configuration (Optional - for Google/GitHub login)
# Get these from:
# - Google: https://console.cloud.google.com/apis/credentials
#   - Create OAuth 2.0 Client ID
#   - Authorized redirect URI: http://localhost:3000/auth/callback
# - GitHub: https://github.com/settings/developers
#   - Create OAuth App
#   - Authorization callback URL: http://localhost:3000/auth/callback
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id
NEXT_PUBLIC_GITHUB_CLIENT_ID=your-github-client-id
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## OAuth Setup

### Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Set Application type to "Web application"
6. Add authorized redirect URI: `http://localhost:3000/auth/callback` (for local) or your production URL
7. Copy the Client ID and add it to `.env.local` as `NEXT_PUBLIC_GOOGLE_CLIENT_ID`

### GitHub OAuth Setup
1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in:
   - Application name: Your app name
   - Homepage URL: Your app URL
   - Authorization callback URL: `http://localhost:3000/auth/callback` (for local) or your production URL
4. Copy the Client ID and add it to `.env.local` as `NEXT_PUBLIC_GITHUB_CLIENT_ID`

**Note:** For production, you'll also need to set the Client Secret in the backend environment variables:
- `MEMORY_GOOGLE_CLIENT_SECRET`
- `MEMORY_GITHUB_CLIENT_SECRET`

## Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── api/               # API routes
│   │   └── health/        # Health check proxy
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home page
│   ├── globals.css        # Global styles
│   ├── icon.tsx           # Favicon
│   └── apple-icon.tsx     # Apple touch icon
├── lib/                   # Utility libraries
│   ├── api-client.ts      # API client for backend
│   ├── types.ts           # TypeScript type definitions
│   └── utils.ts           # Utility functions
├── middleware.ts          # Next.js middleware
└── Configuration files    # package.json, tsconfig.json, etc.
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

## Features

- Landing page with product information
- Interactive dashboard for API testing
- Real-time API integration with memorymesh backend
- TypeScript for type safety
- Tailwind CSS for styling
- Responsive design

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com)
