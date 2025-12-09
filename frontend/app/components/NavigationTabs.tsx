'use client';

import Image from 'next/image';
import { setNavigationState } from '@/lib/api';
import { useEffect, useState } from 'react';

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

    useEffect(() => {
        setMounted(true);
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

    return (
        <div role="navigation" aria-label="Primary" className="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-[rgb(var(--surface-rgb)/0.55)] border-b border-[var(--border)] shadow-[0_8px_32px_rgba(0,0,0,0.06)]">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    <div className="flex items-center space-x-3">
                        <Image src="/logo.png" alt="Memory Mesh" width={200} height={56} className="h-14 w-auto" />
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
                    </div>
                </div>
            </div>
        </div>
    );
}