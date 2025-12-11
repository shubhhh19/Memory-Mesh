'use client';

import Image from 'next/image';
import Link from 'next/link';
import { Icon } from '@iconify/react';
import { setNavigationState } from '@/lib/api';
import { useEffect, useState } from 'react';
import { isAuthenticated, getUser, clearAuthTokens } from '@/lib/auth';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';

interface NavigationTabsProps {
    activeTab: string;
    onTabChange: (tab: string) => void;
}

const tabs = [
    { id: 'landing', label: 'Overview' },
    { id: 'dashboard', label: 'Dashboard' }
];

export default function NavigationTabs({ activeTab, onTabChange }: NavigationTabsProps) {
    const [mounted, setMounted] = useState(false);
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [user, setUser] = useState<{ username?: string; avatar_url?: string; full_name?: string; email?: string } | null>(null);
    const [showUserMenu, setShowUserMenu] = useState(false);
    const router = useRouter();

    useEffect(() => {
        setMounted(true);
        setIsLoggedIn(isAuthenticated());
        if (isAuthenticated()) {
            setUser(getUser());
        }
    }, []);

    const handleTabClick = (tabId: string) => {
        onTabChange(tabId);
        if (mounted) {
            setNavigationState(tabId);
            if (typeof window !== 'undefined') {
                const params = new URLSearchParams(window.location.search);
                params.set('view', tabId);
                const url = `${window.location.pathname}?${params.toString()}`;
                window.history.pushState({}, '', url);
            }
        }
    };

    const handleLogout = () => {
        clearAuthTokens();
        setIsLoggedIn(false);
        setUser(null);
        setShowUserMenu(false);
        toast.success('Logged out successfully');
        router.push('/');
        onTabChange('landing');
    };


    return (
        <div role="navigation" aria-label="Primary" className="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-[rgb(var(--surface-rgb)/0.55)] border-b border-[var(--border)] shadow-[0_8px_32px_rgba(0,0,0,0.06)]">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    <div className="flex items-center space-x-3">
                        <Image src="/logo.png" alt="Memory Mesh" width={200} height={56} className="h-16 w-auto" />
                    </div>

                    <div className="flex items-center space-x-6">
                        {tabs.map((tab) => (
                            <a
                                key={tab.id}
                                href={`?view=${tab.id}`}
                                onClick={(e) => { e.preventDefault(); handleTabClick(tab.id); }}
                                className={`text-sm font-medium transition-colors ${activeTab === tab.id
                                    ? 'text-[var(--accent)]'
                                    : 'text-[var(--muted-text)] hover:text-[var(--text)]'
                                    }`}
                            >
                                {tab.label}
                            </a>
                        ))}

                        <a
                            href="https://github.com/shubhhh19/memory-layer"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-[var(--muted-text)] hover:text-[var(--text)] transition-colors"
                        >
                            GitHub
                        </a>

                        {isLoggedIn && user ? (
                            <div className="relative">
                                <button
                                    onClick={() => setShowUserMenu(!showUserMenu)}
                                    className="flex items-center space-x-2 text-sm font-medium text-[var(--text)] hover:text-[var(--accent)] transition-colors"
                                >
                                    {user.avatar_url ? (
                                        <Image src={user.avatar_url} alt={user.username || 'User'} width={32} height={32} className="w-8 h-8 rounded-full" />
                                    ) : (
                                        <div className="w-8 h-8 rounded-full bg-[var(--accent)] flex items-center justify-center text-white">
                                            {user.username?.[0]?.toUpperCase() || 'U'}
                                        </div>
                                    )}
                                    <span>{user.username}</span>
                                    <Icon icon="mdi:chevron-down" className="w-4 h-4" />
                                </button>

                                {showUserMenu && (
                                    <div className="absolute right-0 mt-2 w-48 bg-[var(--surface)] border border-[var(--border)] rounded-lg shadow-lg py-1">
                                        <div className="px-4 py-2 border-b border-[var(--border)]">
                                            <p className="text-sm font-medium text-[var(--text)]">{user.full_name || user.username}</p>
                                            <p className="text-xs text-[var(--muted-text)]">{user.email}</p>
                                        </div>
                                        <button
                                            onClick={handleLogout}
                                            className="w-full text-left px-4 py-2 text-sm text-[var(--text)] hover:bg-[rgb(var(--surface-rgb)/0.5)] transition-colors flex items-center space-x-2"
                                        >
                                            <Icon icon="mdi:logout" className="w-4 h-4" />
                                            <span>Logout</span>
                                        </button>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <Link
                                href="/login"
                                className="text-sm font-medium px-4 py-2 bg-[var(--accent)] text-white rounded-lg hover:opacity-90 transition-opacity"
                            >
                                Login
                            </Link>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}