'use client';

import { motion } from 'framer-motion';
import { Icon } from '@iconify/react';
import Image from 'next/image';
import { useState } from 'react';
import CodeBlock from './CodeBlock';

interface LandingPageProps {
    onNavigateToDashboard: () => void;
}

const competitiveAdvantages = [
    {
        icon: 'material-symbols:psychology',
        title: 'Intelligent Importance Scoring',
        description: 'Unlike simple vector search, Memory Mesh combines recency decay, role-based weights, and explicit importance signals to surface the most relevant memories first.',
        highlight: 'Multi-factor scoring vs. single similarity metric'
    },
    {
        icon: 'material-symbols:rule-settings',
        title: 'Advanced Retention Policies',
        description: 'Rule-based lifecycle management with archive, delete, and cold storage actions. Create complex retention rules based on age, importance, conversation type, and more.',
        highlight: 'Rule engine vs. simple TTL expiration'
    },
    {
        icon: 'material-symbols:blend',
        title: 'Hybrid Search Ranking',
        description: 'Combines vector similarity, importance scores, and temporal decay for smarter results. Not just cosine similarity—intelligent ranking that understands context.',
        highlight: 'Hybrid ranking vs. pure vector search'
    },
    {
        icon: 'material-symbols:account-tree',
        title: 'True Multi-Tenancy',
        description: 'Built-in tenant isolation with secure data separation. Each tenant gets isolated storage, rate limits, and retention policies.',
        highlight: 'Native multi-tenancy vs. manual isolation'
    },
    {
        icon: 'material-symbols:sync',
        title: 'Real-Time Updates',
        description: 'WebSocket support for live conversation updates and streaming search results. Your app stays in sync without polling.',
        highlight: 'Real-time vs. polling-based'
    },
    {
        icon: 'material-symbols:security',
        title: 'Production-Ready Security',
        description: 'Dual authentication (JWT + API keys), role-based access control, Redis-backed rate limiting, and comprehensive monitoring out of the box.',
        highlight: 'Enterprise security vs. basic auth'
    }
];

const whyBetter = [
    {
        competitor: 'Simple Vector DBs',
        theirWay: 'Basic cosine similarity search',
        ourWay: 'Hybrid ranking with importance scoring and temporal decay',
        icon: 'material-symbols:trending-up'
    },
    {
        competitor: 'Generic Memory Services',
        theirWay: 'Simple TTL-based expiration',
        ourWay: 'Rule-based retention engine with archive, delete, and cold storage',
        icon: 'material-symbols:auto-awesome'
    },
    {
        competitor: 'Basic Embedding APIs',
        theirWay: 'Single embedding provider, synchronous only',
        ourWay: 'Multiple providers (Gemini, Sentence Transformers) with async job queue',
        icon: 'material-symbols:extension'
    },
    {
        competitor: 'DIY Solutions',
        theirWay: 'Build your own multi-tenancy, auth, and monitoring',
        ourWay: 'Everything included: JWT auth, API keys, rate limiting, Prometheus metrics',
        icon: 'material-symbols:rocket-launch'
    }
];

const features = [
    {
        icon: 'material-symbols:search',
        title: 'Semantic Search',
        description: 'Vector similarity search powered by pgvector with intelligent hybrid ranking that combines similarity, importance, and recency.'
    },
    {
        icon: 'material-symbols:psychology',
        title: 'Smart Importance Scoring',
        description: 'Multi-factor importance calculation using recency decay, role weights, and explicit importance signals for better result ranking.'
    },
    {
        icon: 'material-symbols:rule-settings',
        title: 'Advanced Retention',
        description: 'Rule-based lifecycle management with archive, delete, and cold storage actions based on complex conditions.'
    },
    {
        icon: 'material-symbols:account-tree',
        title: 'Multi-Tenant Architecture',
        description: 'Built-in tenant isolation with secure data separation, per-tenant rate limits, and isolated retention policies.'
    },
    {
        icon: 'material-symbols:sync',
        title: 'Real-Time WebSockets',
        description: 'Live updates via WebSocket connections for real-time conversation sync and streaming search results.'
    },
    {
        icon: 'material-symbols:security',
        title: 'Enterprise Security',
        description: 'Dual authentication (JWT + API keys), role-based access control, Redis-backed rate limiting, and CORS protection.'
    }
];

const codeExamples = {
    curl: `# Store a message with importance hint
curl -X POST http://localhost:8000/v1/messages \\
  -H "x-api-key: your-api-key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "tenant_id": "your-tenant",
    "conversation_id": "conversation-1",
    "role": "user",
    "content": "This is a critical piece of information",
    "importance": 0.9
  }'

# Search with hybrid ranking (similarity + importance + recency)
curl "http://localhost:8000/v1/memory/search?\\
  tenant_id=your-tenant&\\
  query=critical information&\\
  top_k=5" \\
  -H "x-api-key: your-api-key"`,
    python: `from memorymesh import MemoryMeshClient

client = MemoryMeshClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# Store message with importance
message = await client.store_message(
    tenant_id="your-tenant",
    conversation_id="conv-1",
    role="user",
    content="Important context for future reference",
    importance=0.85  # Explicit importance signal
)

# Search - automatically uses hybrid ranking
results = await client.search(
    tenant_id="your-tenant",
    query="important context",
    top_k=5
)
# Results ranked by: similarity + importance + recency`,
    javascript: `import { MemoryMeshClient } from '@memorymesh/sdk';

const client = new MemoryMeshClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key'
});

// Store with importance scoring
await client.messages.create({
  tenant_id: 'your-tenant',
  conversation_id: 'conv-1',
  role: 'user',
  content: 'Key information to remember',
  importance: 0.8
});

// Search uses hybrid ranking automatically
const results = await client.memory.search({
  tenant_id: 'your-tenant',
  query: 'key information',
  top_k: 5
});`
};

export default function LandingPage({ onNavigateToDashboard }: LandingPageProps) {
    const [activeCodeTab, setActiveCodeTab] = useState('curl');

    return (
        <div className="min-h-screen bg-[var(--background)]">
            {/* Hero Section */}
            <section className="pt-24 pb-16 px-4 sm:px-6 lg:px-8" aria-labelledby="hero-heading">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.8 }}
                            className="max-w-5xl mx-auto"
                        >
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[var(--border)] bg-[rgb(var(--surface-rgb)/0.5)] backdrop-blur-xl mb-8">
                                <Icon icon="material-symbols:auto-awesome" className="w-4 h-4 text-[var(--accent)]" />
                                <span className="text-sm text-[var(--muted-text)]">Smarter than simple vector search</span>
                            </div>
                            
                            <div className="mb-10">
                                <h1 className="text-5xl md:text-6xl font-light mb-2 tracking-tight">
                                    <span className="bg-gradient-to-r from-[var(--accent)] via-blue-500 to-purple-500 bg-clip-text text-transparent font-normal">
                                        Memory Mesh
                                    </span>
                                </h1>
                                <div className="h-px w-24 bg-gradient-to-r from-[var(--accent)] to-transparent mx-auto mt-4"></div>
                            </div>
                            
                            <h2 id="hero-heading" className="text-5xl md:text-7xl font-light text-[var(--text)] mb-6 leading-tight">
                                <span>Memory That</span>
                                <br />
                                <span className="bg-gradient-to-r from-[var(--accent)] to-blue-400 bg-clip-text text-transparent">Actually Understands</span>
                            </h2>

                            <p className="text-xl md:text-2xl text-[var(--muted-text)] mb-4 max-w-3xl mx-auto leading-relaxed">
                                <span>Not just vector search. Intelligent memory with </span>
                                <span className="text-[var(--text)] font-medium">importance scoring</span>
                                <span>, </span>
                                <span className="text-[var(--text)] font-medium">hybrid ranking</span>
                                <span>, and </span>
                                <span className="text-[var(--text)] font-medium">advanced retention policies</span>
                                <span>.</span>
                            </p>

                            <p className="text-lg text-[var(--muted-text)] mb-8 max-w-2xl mx-auto">
                                The only memory service that combines semantic search with intelligent lifecycle management
                            </p>

                            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
                                <button
                                    onClick={onNavigateToDashboard}
                                    className="bg-[var(--accent)] text-[var(--surface)] px-8 py-3 rounded-lg text-lg font-medium hover:opacity-90 transition-opacity flex items-center space-x-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                                    aria-label="Try Dashboard"
                                >
                                    <Icon icon="material-symbols:api" className="w-5 h-5" />
                                    <span>Try Dashboard</span>
                                </button>

                                <a
                                    href="https://github.com/shubhhh19/memory-layer"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="border border-[var(--border)] text-[var(--text)] px-8 py-3 rounded-lg text-lg font-medium hover:bg-[rgb(var(--surface-rgb)/0.4)] backdrop-blur-xl transition-colors flex items-center space-x-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                                    aria-label="View on GitHub"
                                >
                                    <Icon icon="mdi:github" className="w-5 h-5" />
                                    <span>View on GitHub</span>
                                </a>
                            </div>
                        </motion.div>
                    </div>
                </div>
            </section>

            {/* Why Better Section */}
            <section className="py-20 px-4 sm:px-6 lg:px-8 bg-[rgb(var(--surface-rgb)/0.3)] backdrop-blur-xl" aria-labelledby="why-heading">
                <div className="max-w-7xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8 }}
                        className="text-center mb-16"
                    >
                        <h2 id="why-heading" className="text-4xl md:text-5xl font-light text-[var(--text)] mb-4">
                            <span>Why Memory Mesh is Different</span>
                        </h2>
                        <p className="text-xl text-[var(--muted-text)] max-w-2xl mx-auto">
                            <span>We don&apos;t just store vectors. We build intelligent memory systems.</span>
                        </p>
                    </motion.div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        {whyBetter.map((item, index) => (
                            <motion.div
                                key={item.competitor}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.8, delay: index * 0.1 }}
                                className="rounded-2xl p-6 border border-[var(--border)] bg-[rgb(var(--surface-rgb)/0.55)] backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.06)]"
                            >
                                <div className="flex items-start mb-4">
                                    <div className="p-2 bg-[rgb(var(--surface-rgb)/0.5)] backdrop-blur-xl rounded-lg mr-4 border border-[var(--border)]">
                                        <Icon icon={item.icon} className="w-6 h-6 text-[var(--accent)]" />
                                    </div>
                                    <div className="flex-1">
                                        <h3 className="text-lg font-medium text-[var(--text)] mb-2">{item.competitor}</h3>
                                        <div className="space-y-3">
                                            <div className="flex items-start">
                                                <div className="flex-shrink-0 w-2 h-2 rounded-full bg-red-400 mt-2 mr-3"></div>
                                                <div>
                                                    <p className="text-sm font-medium text-[var(--muted-text)] mb-1">Their Way</p>
                                                    <p className="text-sm text-[var(--muted-text)]">{item.theirWay}</p>
                                                </div>
                                            </div>
                                            <div className="flex items-start">
                                                <div className="flex-shrink-0 w-2 h-2 rounded-full bg-[var(--accent)] mt-2 mr-3"></div>
                                                <div>
                                                    <p className="text-sm font-medium text-[var(--accent)] mb-1">Memory Mesh</p>
                                                    <p className="text-sm text-[var(--text)]">{item.ourWay}</p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Competitive Advantages */}
            <section className="py-20 px-4 sm:px-6 lg:px-8" aria-labelledby="advantages-heading">
                <div className="max-w-7xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8 }}
                        className="text-center mb-16"
                    >
                        <h2 id="advantages-heading" className="text-4xl md:text-5xl font-light text-[var(--text)] mb-4">
                            <span>What Makes Us Better</span>
                        </h2>
                        <p className="text-xl text-[var(--muted-text)] max-w-2xl mx-auto">
                            <span>Features that set Memory Mesh apart from simple vector databases</span>
                        </p>
                    </motion.div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {competitiveAdvantages.map((advantage, index) => (
                            <motion.div
                                key={advantage.title}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.8, delay: index * 0.1 }}
                                className="rounded-2xl p-6 border border-[var(--border)] bg-[rgb(var(--surface-rgb)/0.55)] backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.06)] hover:shadow-[0_12px_40px_rgba(0,0,0,0.08)] transition-shadow"
                            >
                                <div className="flex items-center mb-4">
                                    <div className="p-2 bg-[rgb(var(--surface-rgb)/0.5)] backdrop-blur-xl rounded-lg mr-4 border border-[var(--border)]">
                                        <Icon icon={advantage.icon} className="w-6 h-6 text-[var(--accent)]" />
                                    </div>
                                    <h3 className="text-xl font-medium text-[var(--text)]">{advantage.title}</h3>
                                </div>
                                <p className="text-[var(--muted-text)] text-sm leading-relaxed mb-3">{advantage.description}</p>
                                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[rgb(var(--accent-rgb)/0.1)] border border-[rgb(var(--accent-rgb)/0.2)]">
                                    <Icon icon="material-symbols:check-circle" className="w-4 h-4 text-[var(--accent)]" />
                                    <span className="text-xs font-medium text-[var(--accent)]">{advantage.highlight}</span>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="py-20 px-4 sm:px-6 lg:px-8 bg-[rgb(var(--surface-rgb)/0.3)] backdrop-blur-xl" aria-labelledby="features-heading">
                <div className="max-w-7xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8 }}
                        className="text-center mb-16"
                    >
                        <h2 id="features-heading" className="text-4xl font-light text-[var(--text)] mb-4">
                            <span>Complete Memory Infrastructure</span>
                        </h2>
                        <p className="text-xl text-[var(--muted-text)] max-w-2xl mx-auto">
                            <span>Everything you need for production AI applications</span>
                        </p>
                    </motion.div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {features.map((feature, index) => (
                            <motion.div
                                key={feature.title}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.8, delay: index * 0.1 }}
                                className="rounded-2xl p-6 border border-[var(--border)] bg-[rgb(var(--surface-rgb)/0.55)] backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.06)] hover:shadow-[0_12px_40px_rgba(0,0,0,0.08)] transition-shadow"
                            >
                                <div className="flex items-center mb-4">
                                    <div className="p-2 bg-[rgb(var(--surface-rgb)/0.5)] backdrop-blur-xl rounded-lg mr-4 border border-[var(--border)]">
                                        <Icon icon={feature.icon} className="w-6 h-6 text-[var(--accent)]" />
                                    </div>
                                    <h3 className="text-xl font-medium text-[var(--text)]">{feature.title}</h3>
                                </div>
                                <p className="text-[var(--muted-text)] text-sm leading-relaxed">{feature.description}</p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Code Examples */}
            <section className="py-20 px-4 sm:px-6 lg:px-8" aria-labelledby="code-heading">
                <div className="max-w-6xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8 }}
                        className="text-center mb-12"
                    >
                        <h2 id="code-heading" className="text-4xl font-light text-[var(--text)] mb-4">
                            <span>Get Started in Minutes</span>
                        </h2>
                        <p className="text-xl text-[var(--muted-text)]">
                            <span>Simple API with intelligent defaults. Importance scoring and hybrid ranking work automatically.</span>
                        </p>
                    </motion.div>

                    <div className="mb-8">
                        <div className="flex flex-wrap justify-center gap-2" role="tablist" aria-label="Code language selector">
                            {Object.entries(codeExamples).map(([key]) => (
                                <button
                                    key={key}
                                    onClick={() => setActiveCodeTab(key)}
                                    role="tab"
                                    aria-selected={activeCodeTab === key}
                                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${activeCodeTab === key
                                        ? 'bg-[var(--accent)] text-[var(--surface)]'
                                        : 'bg-[rgb(var(--surface-rgb)/0.6)] backdrop-blur-xl text-[var(--muted-text)] border border-[var(--border)] hover:bg-[rgb(var(--surface-rgb)/0.5)]'
                                        }`}
                                >
                                    {key === 'curl' ? 'cURL' : key === 'javascript' ? 'JavaScript' : key.charAt(0).toUpperCase() + key.slice(1)}
                                </button>
                            ))}
                        </div>
                    </div>

                    <CodeBlock
                        code={codeExamples[activeCodeTab as keyof typeof codeExamples]}
                        language={activeCodeTab === 'curl' ? 'bash' : activeCodeTab === 'javascript' ? 'javascript' : activeCodeTab}
                        showLineNumbers
                    />
                </div>
            </section>

            {/* Footer */}
            <footer className="py-12 px-4 sm:px-6 lg:px-8 bg-[rgb(var(--surface-rgb)/0.6)] backdrop-blur-xl border-t border-[var(--border)]">
                <div className="max-w-7xl mx-auto">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <div className="md:col-span-2">
                            <div className="flex items-center space-x-3 mb-4">
                                <Image src="/logo.png" alt="Memory Mesh Logo" width={120} height={34} className="h-10 w-auto" />
                                <h3 className="text-xl font-medium text-[var(--text)]">Memory Mesh</h3>
                            </div>
                            <p className="text-[var(--muted-text)] text-sm mb-6">
                                <span>Intelligent memory infrastructure for AI applications. </span>
                                <span>Not just vector search—smarter memory with importance scoring, hybrid ranking, and advanced retention.</span>
                            </p>
                            <p className="text-[var(--muted-text)] text-xs mb-2">
                                <span>© 2025 Memory Mesh. Open source project.</span>
                            </p>
                            <p className="text-[var(--muted-text)] text-xs">
                                <span>Made by </span>
                                <a
                                    href="https://shubhsoni.com/"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-[var(--accent)] hover:underline"
                                >
                                    Shubh Soni
                                </a>
                            </p>
                        </div>

                        <div>
                            <h4 className="text-sm font-medium mb-4 text-[var(--text)]">Connect</h4>
                            <ul className="space-y-2 text-sm text-[var(--muted-text)]">
                                <li>
                                    <a href="https://github.com/shubhhh19/memory-layer" target="_blank" rel="noopener noreferrer" className="hover:text-[var(--text)] transition-colors">
                                        <span>GitHub</span>
                                    </a>
                                </li>
                                <li>
                                    <a href="https://shubhsoni.com/" target="_blank" rel="noopener noreferrer" className="hover:text-[var(--text)] transition-colors">
                                        <span>Creator&apos;s Website</span>
                                    </a>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
}
