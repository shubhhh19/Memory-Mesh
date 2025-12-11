'use client';

import { useState, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import NavigationTabs from './components/NavigationTabs';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';
import ProtectedRoute from './components/auth/ProtectedRoute';
import { getNavigationState } from '@/lib/api';

export default function Home() {
    const [activeTab, setActiveTab] = useState('landing');
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        // Set mounted immediately
        setMounted(true);

        // Check URL for view parameter (routes mode)
        if (typeof window !== 'undefined') {
            const params = new URLSearchParams(window.location.search);
            const view = params.get('view');
            if (view === 'dashboard' || view === 'landing') {
                setActiveTab(view);
            } else {
                const savedState = getNavigationState();
                setActiveTab(savedState || 'landing');
            }

            // Handle browser back/forward
            const onPop = () => {
                const params = new URLSearchParams(window.location.search);
                const view = params.get('view');
                setActiveTab(view === 'dashboard' ? 'dashboard' : 'landing');
            };
            window.addEventListener('popstate', onPop);
            return () => window.removeEventListener('popstate', onPop);
        }
    }, []);

    const handleNavigateToDashboard = () => {
        // Navigate to dashboard (authentication check removed for demo)
        // Users can access dashboard to see "coming soon" overlays
        setActiveTab('dashboard');
        if (typeof window !== 'undefined') {
            const params = new URLSearchParams(window.location.search);
            params.set('view', 'dashboard');
            const url = `${window.location.pathname}?${params.toString()}`;
            window.history.pushState({}, '', url);
        }
    };

    // Don't render until mounted to prevent hydration mismatch
    if (!mounted) {
        return (
            <div className="min-h-screen bg-[var(--background)] flex items-center justify-center">
                <div className="animate-pulse flex items-center space-x-2">
                    <div className="w-2 h-2 bg-[var(--accent)] rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-[var(--accent)] rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-[var(--accent)] rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
            </div>
        );
    }

    return (
        <>
            <NavigationTabs activeTab={activeTab} onTabChange={setActiveTab} />

            <main>
                {activeTab === 'landing' ? (
                    <LandingPage onNavigateToDashboard={handleNavigateToDashboard} />
                ) : (
                    <ProtectedRoute>
                        <Dashboard />
                    </ProtectedRoute>
                )}
            </main>

            <Toaster
                position="bottom-right"
                toastOptions={{
                    duration: 4000,
                    style: {
                        background: 'rgb(var(--surface-rgb) / 0.7)',
                        color: 'var(--text)',
                        fontSize: '14px',
                        border: '1px solid var(--border)',
                        backdropFilter: 'blur(12px)'
                    },
                    success: {
                        style: {
                            background: 'rgb(var(--surface-rgb) / 0.7)',
                            color: 'var(--text)',
                            border: '1px solid var(--border)',
                            backdropFilter: 'blur(12px)'
                        },
                    },
                    error: {
                        style: {
                            background: 'rgb(var(--surface-rgb) / 0.7)',
                            color: 'var(--text)',
                            border: '1px solid var(--border)',
                            backdropFilter: 'blur(12px)'
                        },
                    },
                }}
            />
        </>
    );
}