'use client';

import { useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { memoryMeshAPI } from '@/lib/api';
import { setAuthTokens, setUser } from '@/lib/auth';
import toast from 'react-hot-toast';

function OAuthCallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();

    useEffect(() => {
        const handleCallback = async () => {
            // Get params from URL directly as fallback
            const urlParams = new URLSearchParams(window.location.search);
            const code = searchParams.get('code') || urlParams.get('code');
            const state = searchParams.get('state') || urlParams.get('state');
            const error = searchParams.get('error') || urlParams.get('error');

            if (error) {
                toast.error(`OAuth error: ${error}`);
                router.push('/login');
                return;
            }

            if (!code || !state) {
                toast.error('Missing authorization code or state. Please try logging in again.');
                setTimeout(() => router.push('/login'), 2000);
                return;
            }

            try {
                // Determine provider from session storage (set during OAuth initiation)
                const provider = sessionStorage.getItem('oauth_provider') || 'google';
                
                const response = await memoryMeshAPI.oauthCallback(
                    provider as 'google' | 'github',
                    code,
                    state
                );

                if (response.error || !response.data) {
                    toast.error(response.error || 'OAuth authentication failed');
                    router.push('/login');
                    return;
                }

                // Save tokens (this uses encrypted storage)
                if (response.data.access_token) {
                    setAuthTokens({
                        access_token: response.data.access_token,
                        refresh_token: response.data.refresh_token || '',
                        expires_in: response.data.expires_in || 1800
                    });

                    // Get user info
                    const userResponse = await memoryMeshAPI.getCurrentUser();
                    if (userResponse.data) {
                        setUser(userResponse.data);
                    }

                    // Clear provider from session
                    sessionStorage.removeItem('oauth_provider');

                    toast.success('Logged in successfully');
                    router.push('/?view=dashboard');
                } else {
                    toast.error('Invalid response from server');
                    router.push('/login');
                }
            } catch (error) {
                toast.error('An error occurred during authentication');
                router.push('/login');
            }
        };

        handleCallback();
    }, [searchParams, router]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
            <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                <p className="text-gray-600">Completing authentication...</p>
            </div>
        </div>
    );
}

export default function OAuthCallbackPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
                <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                    <p className="text-gray-600">Loading...</p>
                </div>
            </div>
        }>
            <OAuthCallbackContent />
        </Suspense>
    );
}
