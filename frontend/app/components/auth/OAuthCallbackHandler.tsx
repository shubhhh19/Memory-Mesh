'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { setAuthTokens, setUser } from '@/lib/auth';
import { memoryMeshAPI } from '@/lib/api';
import toast from 'react-hot-toast';

export default function OAuthCallbackHandler() {
    const router = useRouter();
    const searchParams = useSearchParams();

    useEffect(() => {
        const handleCallback = async () => {
            // Check for tokens in cookies (set by server-side callback)
            const authTokensCookie = document.cookie
                .split('; ')
                .find(row => row.startsWith('auth_tokens='));

            if (authTokensCookie) {
                try {
                    const tokensJson = decodeURIComponent(authTokensCookie.split('=')[1]);
                    const tokens = JSON.parse(tokensJson);

                    // Save tokens to localStorage
                    setAuthTokens(tokens);

                    // Get user info
                    const userResponse = await memoryMeshAPI.getCurrentUser();
                    if (userResponse.data) {
                        setUser(userResponse.data);
                    }

                    // Clear cookie
                    document.cookie = 'auth_tokens=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';

                    toast.success('Logged in successfully');
                    router.push('/?view=dashboard');
                } catch {
                    toast.error('Authentication failed');
                    router.push('/login');
                }
            } else {
                // Check for error in URL
                const error = searchParams.get('error');
                if (error) {
                    toast.error(`Authentication failed: ${error}`);
                }
                router.push('/login');
            }
        };

        handleCallback();
    }, [router, searchParams]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
            <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Completing authentication...</p>
            </div>
        </div>
    );
}
