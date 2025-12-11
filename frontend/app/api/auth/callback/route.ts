import { NextRequest, NextResponse } from 'next/server';

// This route is kept for backward compatibility but redirects to the client-side callback page
export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams;
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');

    // Redirect to client-side callback page with all parameters
    const callbackUrl = new URL('/auth/callback', request.url);
    if (code) callbackUrl.searchParams.set('code', code);
    if (state) callbackUrl.searchParams.set('state', state);
    if (error) callbackUrl.searchParams.set('error', error);

    return NextResponse.redirect(callbackUrl);
}
