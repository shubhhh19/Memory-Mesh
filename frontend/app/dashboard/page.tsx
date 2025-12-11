'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated } from '@/lib/auth';

export default function DashboardPage() {
    const router = useRouter();

    useEffect(() => {
        // Redirect to home page with dashboard view
        // This allows users to access both landing page and dashboard
        if (typeof window !== 'undefined') {
            if (isAuthenticated()) {
                router.replace('/?view=dashboard');
            } else {
                router.replace('/login');
            }
        }
    }, [router]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-[var(--background)]">
            <div className="animate-pulse flex items-center space-x-2">
                <div className="w-2 h-2 bg-[var(--accent)] rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-[var(--accent)] rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-[var(--accent)] rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
        </div>
    );
}
