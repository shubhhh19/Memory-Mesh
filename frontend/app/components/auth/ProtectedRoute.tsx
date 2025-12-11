'use client';

import { useEffect, useState } from 'react';

interface ProtectedRouteProps {
    children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
    const [isChecking, setIsChecking] = useState(true);

    useEffect(() => {
        // Allow dashboard access without authentication for demo purposes
        // Users can still configure API settings and see "coming soon" overlays
        setIsChecking(false);
    }, []);

    if (isChecking) {
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

    return <>{children}</>;
}
