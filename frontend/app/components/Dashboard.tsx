'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Icon } from '@iconify/react';
import { getConfig } from '@/lib/api';
import ConfigurationPanel from './dashboard/ConfigurationPanel';
import MessageManagement from './dashboard/MessageManagement';
import SearchSection from './dashboard/SearchSection';
import MessageRetrieval from './dashboard/MessageRetrieval';
import AdminSection from './dashboard/AdminSection';
import RequestInspector from './dashboard/RequestInspector';
import HybridRankingVisualizer from './dashboard/HybridRankingVisualizer';
import ComingSoonOverlay from './dashboard/ComingSoonOverlay';

type DashboardSection =
    | 'config'
    | 'messages'
    | 'search'
    | 'ranking'
    | 'retrieve'
    | 'admin'
    | 'history';

const sections = [
    {
        id: 'config' as const,
        label: 'Configuration',
        icon: 'material-symbols:settings',
        description: 'API settings and connection'
    },
    {
        id: 'messages' as const,
        label: 'Messages',
        icon: 'material-symbols:add-circle',
        description: 'Store and manage messages'
    },
    {
        id: 'search' as const,
        label: 'Search',
        icon: 'material-symbols:search',
        description: 'Semantic memory search'
    },
    {
        id: 'ranking' as const,
        label: 'Hybrid Ranking',
        icon: 'material-symbols:bar-chart',
        description: 'Interactive ranking visualizer'
    },
    {
        id: 'retrieve' as const,
        label: 'Retrieve',
        icon: 'material-symbols:download',
        description: 'Get message by ID'
    },
    {
        id: 'admin' as const,
        label: 'Admin',
        icon: 'material-symbols:admin-panel-settings',
        description: 'Health & retention'
    },
    {
        id: 'history' as const,
        label: 'History',
        icon: 'material-symbols:history',
        description: 'Request inspector'
    }
];

export default function Dashboard() {
    const [activeSection, setActiveSection] = useState<DashboardSection>('config');
    const [configChanged, setConfigChanged] = useState(0);
    const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');

    const handleConfigChange = () => {
        setConfigChanged(prev => prev + 1);
        // Recheck API status when config changes
        checkApiHealth();
    };

    const checkApiHealth = async () => {
        try {
            const config = getConfig();
            if (!config.baseUrl) {
                setApiStatus('disconnected');
                return;
            }

            const response = await fetch(`${config.baseUrl}/v1/admin/health`, {
                method: 'GET',
                headers: config.apiKey ? { 'x-api-key': config.apiKey } : {},
            });

            if (response.ok) {
                setApiStatus('connected');
            } else {
                setApiStatus('disconnected');
            }
        } catch {
            setApiStatus('disconnected');
        }
    };

    // Check API health on mount and periodically
    useEffect(() => {
        checkApiHealth();
        const interval = setInterval(checkApiHealth, 10000);
        return () => clearInterval(interval);
    }, [configChanged]);
    const onSidebarKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
        const index = sections.findIndex(s => s.id === activeSection);
        if (e.key === 'ArrowDown') {
            const next = (index + 1) % sections.length;
            setActiveSection(sections[next].id);
        } else if (e.key === 'ArrowUp') {
            const prev = (index - 1 + sections.length) % sections.length;
            setActiveSection(sections[prev].id);
        } else if (e.key === 'Home') {
            setActiveSection(sections[0].id);
        } else if (e.key === 'End') {
            setActiveSection(sections[sections.length - 1].id);
        }
    };

    const renderSectionContent = () => {
        const needsBackend = apiStatus !== 'connected';
        
        switch (activeSection) {
            case 'config':
                return <ConfigurationPanel onConfigChange={handleConfigChange} />;
            case 'messages':
                if (needsBackend) {
                    return (
                        <ComingSoonOverlay 
                            feature="Message Management"
                            description="Store, update, and manage conversational messages with automatic embedding generation and importance scoring. Messages are processed with vector embeddings and ranked by our hybrid algorithm."
                        />
                    );
                }
                return <MessageManagement key={configChanged} />;
            case 'search':
                if (needsBackend) {
                    return (
                        <ComingSoonOverlay 
                            feature="Semantic Memory Search"
                            description="Search through your memories using vector similarity with intelligent hybrid ranking that combines similarity (60%), importance (30%), and temporal decay (10%) for smarter results."
                        />
                    );
                }
                return <SearchSection key={configChanged} />;
            case 'ranking':
                if (needsBackend) {
                    return (
                        <ComingSoonOverlay 
                            feature="Hybrid Ranking Visualizer"
                            description="Interactively explore how Memory Mesh combines vector similarity, importance scoring, and temporal decay for smarter search results. Adjust weights in real-time and see results re-rank instantly—a feature unique to Memory Mesh."
                        />
                    );
                }
                return <HybridRankingVisualizer key={configChanged} />;
            case 'retrieve':
                if (needsBackend) {
                    return (
                        <ComingSoonOverlay 
                            feature="Message Retrieval"
                            description="Retrieve specific messages by ID with full details including embedding status, importance scores, metadata, and conversation context."
                        />
                    );
                }
                return <MessageRetrieval key={configChanged} />;
            case 'admin':
                if (needsBackend) {
                    return (
                        <ComingSoonOverlay 
                            feature="Admin & Analytics"
                            description="Monitor system health, run retention policies, and view usage analytics. Includes Prometheus metrics, health checks, retention policy management, and comprehensive monitoring."
                        />
                    );
                }
                return <AdminSection key={configChanged} />;
            case 'history':
                return <RequestInspector />;
            default:
                return null;
        }
    };

    return (
        <div className="min-h-screen bg-[var(--background)] pt-16">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8">
                {/* Header */}
                <div className="mb-4 sm:mb-8">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6 }}
                    >
                        <div className="flex flex-col sm:flex-row items-start justify-between gap-4">
                            <div>
                                <h1 className="text-2xl sm:text-3xl font-light text-[var(--text)] mb-2">
                                    <span>Dashboard</span>
                                </h1>
                                <p className="text-[var(--muted-text)]">
                                    <span>Test and explore Memory Mesh API endpoints in real-time</span>
                                </p>
                            </div>

                            {/* API Status Indicator */}
                            <div className="flex items-center space-x-3 px-4 py-2.5 rounded-xl bg-[rgb(var(--surface-rgb)/0.6)] border border-[var(--border)] backdrop-blur-xl">
                                <div className={`w-3 h-3 rounded-full ${apiStatus === 'connected' ? 'bg-green-500' :
                                        apiStatus === 'disconnected' ? 'bg-red-500' :
                                            'bg-yellow-500 animate-pulse'
                                    }`}></div>
                                <div>
                                    <p className="text-xs font-medium text-[var(--text)]">
                                        {apiStatus === 'connected' ? 'API Connected' :
                                            apiStatus === 'disconnected' ? 'API Disconnected' :
                                                'Checking...'}
                                    </p>
                                    <p className="text-xs text-[var(--muted-text)]">
                                        {apiStatus === 'connected' ? 'Backend is healthy' :
                                            apiStatus === 'disconnected' ? 'Check configuration' :
                                                'Testing connection...'}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 sm:gap-8">
                    {/* Sidebar Navigation */}
                    <div className="lg:col-span-1">
                        {/* Mobile: Horizontal scroll */}
                        <div className="lg:hidden mb-4 overflow-x-auto -mx-4 px-4">
                            <div className="flex space-x-2 min-w-max">
                                {sections.map((section) => (
                                    <button
                                        key={section.id}
                                        onClick={() => setActiveSection(section.id)}
                                        className={`px-4 py-2 rounded-lg text-sm whitespace-nowrap border transition-colors ${
                                            activeSection === section.id
                                                ? 'border-[var(--accent)] bg-[var(--accent)] text-white'
                                                : 'border-[var(--border)] bg-[rgb(var(--surface-rgb)/0.55)] text-[var(--muted-text)]'
                                        }`}
                                    >
                                        {section.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                        
                        {/* Desktop: Vertical sidebar */}
                        <div className="hidden lg:block rounded-2xl border border-[var(--border)] bg-[rgb(var(--surface-rgb)/0.55)] backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.06)] p-2 sticky top-24">
                            <nav className="space-y-1" role="navigation" aria-label="Dashboard sections" onKeyDown={onSidebarKeyDown}>
                                {sections.map((section, index) => (
                                    <motion.button
                                        key={section.id}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ duration: 0.3, delay: index * 0.05 }}
                                        onClick={() => setActiveSection(section.id)}
                                        className={`w-full text-left px-3 py-3 rounded-lg transition-colors duration-200 flex items-start space-x-3 border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${activeSection === section.id
                                            ? 'border-[var(--accent)] bg-[rgb(var(--surface-rgb)/0.45)] text-[var(--text)]'
                                            : 'border-transparent text-[var(--muted-text)] hover:bg-[rgb(var(--surface-rgb)/0.45)] hover:text-[var(--text)]'
                                            }`}
                                        aria-current={activeSection === section.id ? 'page' : undefined}
                                        tabIndex={0}
                                    >
                                        <Icon
                                            icon={section.icon}
                                            className={`w-5 h-5 mt-0.5 flex-shrink-0 ${activeSection === section.id ? 'text-[var(--accent)]' : 'text-[var(--muted-text)]'
                                                }`}
                                        />
                                        <div className="min-w-0 flex-1">
                                            <p className="text-sm font-medium">{section.label}</p>
                                            <p className="text-xs text-[var(--muted-text)] mt-0.5 leading-tight">
                                                {section.description}
                                            </p>
                                        </div>
                                    </motion.button>
                                ))}
                            </nav>

                            {/* API Endpoints - Hidden on mobile */}
                            <div className="mt-6 pt-6 border-t border-[var(--border)] mobile-hidden">
                                <h4 className="text-xs font-medium text-[var(--muted-text)] uppercase tracking-wider mb-3">
                                    API Endpoints
                                </h4>
                                <div className="space-y-2">
                                    <div className="text-xs">
                                        <code className="text-[var(--accent)] font-mono">POST /v1/messages</code>
                                        <p className="text-[var(--muted-text)] mt-0.5">Store messages</p>
                                    </div>
                                    <div className="text-xs">
                                        <code className="text-[var(--accent)] font-mono">GET /v1/memory/search</code>
                                        <p className="text-[var(--muted-text)] mt-0.5">Semantic search</p>
                                    </div>
                                    <div className="text-xs">
                                        <code className="text-[var(--accent)] font-mono">GET /v1/memory/retrieve</code>
                                        <p className="text-[var(--muted-text)] mt-0.5">Get by ID</p>
                                    </div>
                                </div>
                            </div>

                            {/* Quick Tips */}
                            <div className="mt-6 pt-6 border-t border-[var(--border)]">
                                <h4 className="text-xs font-medium text-[var(--muted-text)] uppercase tracking-wider mb-3">
                                    Quick Tips
                                </h4>
                                <div className="space-y-2 text-xs text-[var(--muted-text)]">
                                    <div className="flex items-start space-x-2">
                                        <Icon icon="material-symbols:lightbulb" className="w-3 h-3 mt-0.5 text-[var(--accent)] flex-shrink-0" />
                                        <span>Configure API settings first</span>
                                    </div>
                                    <div className="flex items-start space-x-2">
                                        <Icon icon="material-symbols:lightbulb" className="w-3 h-3 mt-0.5 text-[var(--accent)] flex-shrink-0" />
                                        <span>Check History for request logs</span>
                                    </div>
                                    <div className="flex items-start space-x-2">
                                        <Icon icon="material-symbols:lightbulb" className="w-3 h-3 mt-0.5 text-[var(--accent)] flex-shrink-0" />
                                        <span>Use unique tenant IDs</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Main Content */}
                    <div className="lg:col-span-3">
                        {/* Mobile section title */}
                        <div className="lg:hidden mb-4">
                            <h2 className="text-xl font-semibold">
                                {sections.find(s => s.id === activeSection)?.label}
                            </h2>
                            <p className="text-sm text-[var(--muted-text)]">
                                {sections.find(s => s.id === activeSection)?.description}
                            </p>
                        </div>
                        <motion.div
                            key={activeSection}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            transition={{ duration: 0.3 }}
                            className="space-y-6"
                        >
                            {renderSectionContent()}
                        </motion.div>
                    </div>
                </div>

                {/* Footer Help */}
                <div className="mt-12 pt-8 border-t border-[var(--border)]">
                    <div className="rounded-2xl p-6 border border-[var(--border)] bg-[rgb(var(--surface-rgb)/0.55)] backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.06)]">
                        <div className="flex items-start space-x-4">
                            <div className="flex-shrink-0">
                                <Icon icon="material-symbols:info" className="w-6 h-6 text-[var(--accent)]" />
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-[var(--text)] mb-1">
                                    <span>Getting Started</span>
                                </h3>
                                <p className="text-sm text-[var(--muted-text)] mb-3">
                                    <span>Configure your API connection in the Configuration section, then use the other tabs to test different endpoints. </span>
                                    <span>All requests are logged in the History section for debugging.</span>
                                </p>
                                <div className="flex flex-wrap gap-2">
                                    <a
                                        href="https://docs.memory-mesh.com"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center space-x-1 text-xs text-[var(--muted-text)] hover:text-[var(--text)] transition-colors"
                                    >
                                        <Icon icon="material-symbols:book" className="w-3 h-3" />
                                        <span>Documentation</span>
                                    </a>
                                    <a
                                        href="https://docs.memory-mesh.com/api"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center space-x-1 text-xs text-[var(--muted-text)] hover:text-[var(--text)] transition-colors"
                                    >
                                        <Icon icon="material-symbols:api" className="w-3 h-3" />
                                        <span>API Reference</span>
                                    </a>
                                    <a
                                        href="https://github.com/memory-mesh/examples"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center space-x-1 text-xs text-[var(--muted-text)] hover:text-[var(--text)] transition-colors"
                                    >
                                        <Icon icon="material-symbols:code" className="w-3 h-3" />
                                        <span>Examples</span>
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}