'use client';

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Icon } from '@iconify/react';
import toast from 'react-hot-toast';
import { getConfig } from '@/lib/api';

interface SearchResult {
  message_id: string;
  score: number;
  similarity: number;
  decay: number;
  importance: number | null;
  content: string;
  role: string;
  created_at: string;
}

interface RankingWeights {
  similarity: number;
  importance: number;
  decay: number;
}

export default function HybridRankingVisualizer() {
  const [searchQuery, setSearchQuery] = useState('');
  const [tenantId, setTenantId] = useState('demo-tenant');
  const [topK, setTopK] = useState(5);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [weights, setWeights] = useState<RankingWeights>({
    similarity: 0.6,
    importance: 0.3,
    decay: 0.1
  });

  // Recalculate scores when weights change
  const recalculatedResults = useMemo(() => {
    if (results.length === 0) return [];
    
    return results.map(result => {
      const importance = result.importance ?? 0;
      const newScore = 
        result.similarity * weights.similarity +
        importance * weights.importance +
        result.decay * weights.decay;
      
      return {
        ...result,
        recalculatedScore: newScore
      };
    }).sort((a, b) => b.recalculatedScore - a.recalculatedScore);
  }, [results, weights]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      toast.error('Please enter a search query');
      return;
    }

    setIsLoading(true);
    try {
      const config = getConfig();
      const response = await fetch(
        `${config.baseUrl}/v1/memory/search?tenant_id=${tenantId}&query=${encodeURIComponent(searchQuery)}&top_k=${topK}`,
        {
          headers: {
            'x-api-key': config.apiKey || '',
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      // Handle both response formats: {items: [...]} or {results: [...]}
      const items = data.items || data.results || [];
      if (items.length > 0) {
        setResults(items);
        toast.success(`Found ${items.length} results`);
      } else {
        setResults([]);
        toast('No results found', { icon: 'ℹ️' });
      }
    } catch {
      toast.error('Failed to search memories');
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const updateWeight = (key: keyof RankingWeights, value: number) => {
    const newWeights = { ...weights, [key]: value };
    const total = newWeights.similarity + newWeights.importance + newWeights.decay;
    
    // Normalize to sum to 1.0
    setWeights({
      similarity: newWeights.similarity / total,
      importance: newWeights.importance / total,
      decay: newWeights.decay / total
    });
  };

  const resetWeights = () => {
    setWeights({ similarity: 0.6, importance: 0.3, decay: 0.1 });
  };

  const getRankingReason = (result: SearchResult & { recalculatedScore: number }) => {
    const similarityContribution = result.similarity * weights.similarity;
    const importanceContribution = (result.importance ?? 0) * weights.importance;
    const decayContribution = result.decay * weights.decay;
    
    const maxContribution = Math.max(similarityContribution, importanceContribution, decayContribution);
    
    if (maxContribution === similarityContribution) {
      return { reason: 'similarity', color: 'bg-blue-500', icon: 'material-symbols:search' };
    } else if (maxContribution === importanceContribution) {
      return { reason: 'importance', color: 'bg-yellow-500', icon: 'material-symbols:star' };
    } else {
      return { reason: 'recency', color: 'bg-green-500', icon: 'material-symbols:schedule' };
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-[var(--border)] bg-[rgb(var(--surface-rgb)/0.55)] backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.06)] p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-light text-[var(--text)] mb-2">
              Hybrid Ranking Visualizer
            </h2>
            <p className="text-sm text-[var(--muted-text)]">
              See how Memory Mesh combines vector similarity, importance scoring, and temporal decay for smarter results
            </p>
          </div>
          <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-[rgb(var(--accent-rgb)/0.1)] border border-[rgb(var(--accent-rgb)/0.2)]">
            <Icon icon="material-symbols:auto-awesome" className="w-4 h-4 text-[var(--accent)]" />
            <span className="text-xs font-medium text-[var(--accent)]">Unique Feature</span>
          </div>
        </div>

        {/* Search Form */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-[var(--muted-text)] mb-1">
              Search Query
            </label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Enter search query..."
              className="w-full px-3 py-2 border border-[var(--border)] rounded-md text-sm bg-[rgb(var(--surface-rgb)/0.6)] backdrop-blur-xl text-[var(--text)] focus:ring-2 focus:ring-[var(--accent)]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--muted-text)] mb-1">
              Tenant ID
            </label>
            <input
              type="text"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              className="w-full px-3 py-2 border border-[var(--border)] rounded-md text-sm bg-[rgb(var(--surface-rgb)/0.6)] backdrop-blur-xl text-[var(--text)] focus:ring-2 focus:ring-[var(--accent)]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--muted-text)] mb-1">
              Top K
            </label>
            <input
              type="number"
              min="1"
              max="10"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
              className="w-full px-3 py-2 border border-[var(--border)] rounded-md text-sm bg-[rgb(var(--surface-rgb)/0.6)] backdrop-blur-xl text-[var(--text)] focus:ring-2 focus:ring-[var(--accent)]"
            />
          </div>
        </div>

        <button
          onClick={handleSearch}
          disabled={isLoading}
          className="w-full bg-[var(--accent)] text-[var(--surface)] px-4 py-2 rounded-md font-medium hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center justify-center space-x-2"
        >
          {isLoading ? (
            <>
              <Icon icon="material-symbols:progress-activity" className="w-4 h-4 animate-spin" />
              <span>Searching...</span>
            </>
          ) : (
            <>
              <Icon icon="material-symbols:search" className="w-4 h-4" />
              <span>Search & Visualize</span>
            </>
          )}
        </button>
      </div>

      {/* Weight Controls */}
      {results.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-[var(--border)] bg-[rgb(var(--surface-rgb)/0.55)] backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.06)] p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-[var(--text)]">Adjust Ranking Weights</h3>
            <button
              onClick={resetWeights}
              className="text-xs text-[var(--muted-text)] hover:text-[var(--text)] transition-colors flex items-center space-x-1"
            >
              <Icon icon="material-symbols:refresh" className="w-3 h-3" />
              <span>Reset to Default (60/30/10)</span>
            </button>
          </div>

          <div className="space-y-4">
            {/* Similarity Weight */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <Icon icon="material-symbols:search" className="w-4 h-4 text-blue-500" />
                  <span className="text-sm font-medium text-[var(--text)]">Vector Similarity</span>
                </div>
                <span className="text-sm text-[var(--muted-text)]">{(weights.similarity * 100).toFixed(1)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.similarity * 100}
                onChange={(e) => updateWeight('similarity', parseFloat(e.target.value) / 100)}
                className="w-full h-2 bg-[rgb(var(--surface-rgb)/0.6)] rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>

            {/* Importance Weight */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <Icon icon="material-symbols:star" className="w-4 h-4 text-yellow-500" />
                  <span className="text-sm font-medium text-[var(--text)]">Importance Score</span>
                </div>
                <span className="text-sm text-[var(--muted-text)]">{(weights.importance * 100).toFixed(1)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.importance * 100}
                onChange={(e) => updateWeight('importance', parseFloat(e.target.value) / 100)}
                className="w-full h-2 bg-[rgb(var(--surface-rgb)/0.6)] rounded-lg appearance-none cursor-pointer accent-yellow-500"
              />
            </div>

            {/* Decay Weight */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <Icon icon="material-symbols:schedule" className="w-4 h-4 text-green-500" />
                  <span className="text-sm font-medium text-[var(--text)]">Temporal Decay</span>
                </div>
                <span className="text-sm text-[var(--muted-text)]">{(weights.decay * 100).toFixed(1)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={weights.decay * 100}
                onChange={(e) => updateWeight('decay', parseFloat(e.target.value) / 100)}
                className="w-full h-2 bg-[rgb(var(--surface-rgb)/0.6)] rounded-lg appearance-none cursor-pointer accent-green-500"
              />
            </div>
          </div>

          <div className="mt-4 p-3 rounded-lg bg-[rgb(var(--surface-rgb)/0.6)] border border-[var(--border)]">
            <p className="text-xs text-[var(--muted-text)]">
              <span className="font-medium">Formula:</span> Final Score = (Similarity × {weights.similarity.toFixed(2)}) + (Importance × {weights.importance.toFixed(2)}) + (Decay × {weights.decay.toFixed(2)})
            </p>
          </div>
        </motion.div>
      )}

      {/* Results Visualization */}
      <AnimatePresence>
        {recalculatedResults.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="rounded-2xl border border-[var(--border)] bg-[rgb(var(--surface-rgb)/0.55)] backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.06)]"
          >
            <div className="p-4 border-b border-[var(--border)]">
              <h3 className="text-lg font-medium text-[var(--text)]">
                Ranked Results ({recalculatedResults.length})
              </h3>
              <p className="text-xs text-[var(--muted-text)] mt-1">
                Results re-ranked based on adjusted weights. Drag sliders above to see real-time re-ranking.
              </p>
            </div>

            <div className="divide-y divide-[var(--border)]">
              {recalculatedResults.map((result, index) => {
                const rankingReason = getRankingReason(result);
                const similarityContribution = result.similarity * weights.similarity;
                const importanceContribution = (result.importance ?? 0) * weights.importance;
                const decayContribution = result.decay * weights.decay;

                return (
                  <motion.div
                    key={result.message_id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="p-6 hover:bg-[rgb(var(--surface-rgb)/0.45)] transition-colors"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--accent)] text-[var(--surface)] font-bold text-sm">
                          {index + 1}
                        </div>
                        <div>
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="text-sm font-medium text-[var(--text)] capitalize">{result.role}</span>
                            <div className={`flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs ${rankingReason.color} bg-opacity-20 border border-opacity-30`}>
                              <Icon icon={rankingReason.icon} className="w-3 h-3" />
                              <span className="capitalize">Ranked by {rankingReason.reason}</span>
                            </div>
                          </div>
                          <p className="text-sm text-[var(--text)] line-clamp-2">{result.content}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-[var(--accent)]">
                          {(result.recalculatedScore * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-[var(--muted-text)]">Final Score</div>
                      </div>
                    </div>

                    {/* Score Breakdown */}
                    <div className="space-y-2">
                      <div className="grid grid-cols-3 gap-3">
                        {/* Similarity */}
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-[var(--muted-text)] flex items-center space-x-1">
                              <Icon icon="material-symbols:search" className="w-3 h-3 text-blue-500" />
                              <span>Similarity</span>
                            </span>
                            <span className="text-xs font-medium text-[var(--text)]">
                              {(similarityContribution * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="relative h-2 bg-[rgb(var(--surface-rgb)/0.6)] rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${(result.similarity * 100)}%` }}
                              transition={{ delay: index * 0.1 + 0.2, duration: 0.5 }}
                              className="h-full bg-blue-500"
                            />
                          </div>
                          <div className="text-xs text-[var(--muted-text)] mt-0.5">
                            Raw: {(result.similarity * 100).toFixed(1)}% × {weights.similarity.toFixed(2)}
                          </div>
                        </div>

                        {/* Importance */}
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-[var(--muted-text)] flex items-center space-x-1">
                              <Icon icon="material-symbols:star" className="w-3 h-3 text-yellow-500" />
                              <span>Importance</span>
                            </span>
                            <span className="text-xs font-medium text-[var(--text)]">
                              {(importanceContribution * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="relative h-2 bg-[rgb(var(--surface-rgb)/0.6)] rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${((result.importance ?? 0) * 100)}%` }}
                              transition={{ delay: index * 0.1 + 0.3, duration: 0.5 }}
                              className="h-full bg-yellow-500"
                            />
                          </div>
                          <div className="text-xs text-[var(--muted-text)] mt-0.5">
                            Raw: {((result.importance ?? 0) * 100).toFixed(1)}% × {weights.importance.toFixed(2)}
                          </div>
                        </div>

                        {/* Decay */}
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-[var(--muted-text)] flex items-center space-x-1">
                              <Icon icon="material-symbols:schedule" className="w-3 h-3 text-green-500" />
                              <span>Decay</span>
                            </span>
                            <span className="text-xs font-medium text-[var(--text)]">
                              {(decayContribution * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="relative h-2 bg-[rgb(var(--surface-rgb)/0.6)] rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${(result.decay * 100)}%` }}
                              transition={{ delay: index * 0.1 + 0.4, duration: 0.5 }}
                              className="h-full bg-green-500"
                            />
                          </div>
                          <div className="text-xs text-[var(--muted-text)] mt-0.5">
                            Raw: {(result.decay * 100).toFixed(1)}% × {weights.decay.toFixed(2)}
                          </div>
                        </div>
                      </div>

                      {/* Combined Score Bar */}
                      <div className="mt-3 pt-3 border-t border-[var(--border)]">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-[var(--text)]">Combined Score Breakdown</span>
                        </div>
                        <div className="relative h-4 bg-[rgb(var(--surface-rgb)/0.6)] rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${(similarityContribution / result.recalculatedScore) * 100}%` }}
                            transition={{ delay: index * 0.1 + 0.5, duration: 0.5 }}
                            className="absolute left-0 h-full bg-blue-500"
                            title="Similarity contribution"
                          />
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${(importanceContribution / result.recalculatedScore) * 100}%` }}
                            transition={{ delay: index * 0.1 + 0.6, duration: 0.5 }}
                            className="absolute left-0 h-full bg-yellow-500"
                            style={{ marginLeft: `${(similarityContribution / result.recalculatedScore) * 100}%` }}
                            title="Importance contribution"
                          />
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${(decayContribution / result.recalculatedScore) * 100}%` }}
                            transition={{ delay: index * 0.1 + 0.7, duration: 0.5 }}
                            className="absolute left-0 h-full bg-green-500"
                            style={{ marginLeft: `${((similarityContribution + importanceContribution) / result.recalculatedScore) * 100}%` }}
                            title="Decay contribution"
                          />
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

