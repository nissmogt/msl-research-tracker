import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  Search,
  Loader,
  Database,
  Globe,
  Clock3,
  Zap
} from 'lucide-react';
import ArticleList from './ArticleList';
import ArticleDetail from './ArticleDetail';
import TutorialModal from './TutorialModal';

const SEARCH_CACHE_TTL_MS = 5 * 60 * 1000;
const RECENT_SEARCHES_KEY = 'msl_recent_searches_v1';

function Dashboard() {
  const [articles, setArticles] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [daysBack, setDaysBack] = useState(7);
  const [maxResults, setMaxResults] = useState(10);
  const [loading, setLoading] = useState(false);
  const [searchMode, setSearchMode] = useState('local'); // 'local' or 'pubmed'
  const [showTutorial, setShowTutorial] = useState(() => {
    return localStorage.getItem('msl_tutorial_complete') !== 'true';
  });
  const [searchStatus, setSearchStatus] = useState('Ready');
  const [searchProgress, setSearchProgress] = useState(0);
  const [useCase, setUseCase] = useState('clinical'); // 'clinical' or 'exploratory'
  const [error, setError] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const [recentSearches, setRecentSearches] = useState(() => {
    try {
      const raw = localStorage.getItem(RECENT_SEARCHES_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });

  const searchCacheRef = useRef(new Map());
  const abortControllerRef = useRef(null);
  const progressIntervalRef = useRef(null);
  const searchInputRef = useRef(null);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const onKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const cacheKey = (term, mode, days, currentUseCase, limit) => {
    return `${mode}::${term.trim().toLowerCase()}::${days}::${currentUseCase}::${limit}`;
  };

  const setRecent = (term) => {
    const cleaned = term.trim();
    if (!cleaned) return;
    const next = [cleaned, ...recentSearches.filter((x) => x.toLowerCase() !== cleaned.toLowerCase())].slice(0, 8);
    setRecentSearches(next);
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(next));
  };

  const clearProgressTimer = () => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  };

  const performSearch = async ({
    term,
    mode,
    days,
    currentUseCase,
    limit,
    forceFresh = false,
  }) => {
    const trimmed = term.trim();
    if (!trimmed) return;

    const key = cacheKey(trimmed, mode, days, currentUseCase, limit);
    const cached = searchCacheRef.current.get(key);
    const now = Date.now();

    if (!forceFresh && cached && now - cached.ts < SEARCH_CACHE_TTL_MS) {
      setArticles(cached.data);
      setSearchStatus(`Loaded ${cached.data.length} cached results`);
      setHasSearched(true);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError('');
    setSearchProgress(0);

    try {
      const endpoint = '/articles/search-pubmed';

      setSearchStatus(
        mode === 'pubmed'
          ? 'Searching PubMed + scoring reliability...'
          : 'Searching local-style flow (fast mode)...'
      );

      clearProgressTimer();
      progressIntervalRef.current = setInterval(() => {
        setSearchProgress((prev) => {
          if (prev >= 92) return prev;
          return prev + Math.random() * 8;
        });
      }, 350);

      const response = await axios.post(
        endpoint,
        {
          therapeutic_area: trimmed,
          days_back: days,
          use_case: currentUseCase,
          max_results: limit,
        },
        { signal: controller.signal }
      );

      clearProgressTimer();
      setSearchProgress(100);

      const resultList = Array.isArray(response.data) ? response.data : [];
      searchCacheRef.current.set(key, { ts: Date.now(), data: resultList });
      setArticles(resultList);
      setRecent(trimmed);
      setHasSearched(true);
      setSearchStatus(`Loaded ${resultList.length} result${resultList.length === 1 ? '' : 's'}`);
    } catch (err) {
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
        return;
      }
      console.error('[Dashboard] Error searching articles:', err);
      setHasSearched(true);
      setError(`Search failed: ${err.response?.data?.detail || err.message || 'Unknown error'}. Please try again.`);
      setSearchStatus('Search failed');
    } finally {
      clearProgressTimer();
      setLoading(false);
      setTimeout(() => setSearchProgress(0), 250);
    }
  };

  const handleSearch = async ({ forceFresh = false } = {}) => {
    if (!searchTerm.trim()) {
      setError('Please enter a therapeutic area to search.');
      return;
    }

    await performSearch({
      term: searchTerm,
      mode: searchMode,
      days: daysBack,
      currentUseCase: useCase,
      limit: maxResults,
      forceFresh,
    });
  };

  const handleTutorialClose = () => {
    setShowTutorial(false);
    localStorage.setItem('msl_tutorial_complete', 'true');
  };

  const handleTutorialOpen = () => {
    setShowTutorial(true);
  };

  const handleUseCaseToggle = async (newUseCase) => {
    setUseCase(newUseCase);
    if (searchTerm.trim()) {
      await performSearch({
        term: searchTerm,
        mode: searchMode,
        days: daysBack,
        currentUseCase: newUseCase,
        limit: maxResults,
      });
    }
  };

  const quickAreaSearch = async (area) => {
    setSearchTerm(area);
    await performSearch({
      term: area,
      mode: searchMode,
      days: daysBack,
      currentUseCase: useCase,
      limit: maxResults,
    });
  };

  return (
    <div className="min-h-screen flex bg-gray-50">
      <TutorialModal open={showTutorial} onClose={handleTutorialClose} />

      <button
        onClick={handleTutorialOpen}
        className="fixed bottom-6 right-6 z-40 bg-primary-600 text-white rounded-full w-12 h-12 flex items-center justify-center shadow-lg hover:bg-primary-700 focus:outline-none"
        title="Show tutorial"
        style={{ fontSize: 28, fontWeight: 'bold' }}
        aria-label="Show tutorial"
      >
        ?
      </button>

      <div className="flex-1 flex flex-col">
        <div className="bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8 py-4 sticky top-0 z-20">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Search therapeutic area (e.g., Oncology, Neurology)..."
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                />
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <select
                value={daysBack}
                onChange={(e) => setDaysBack(parseInt(e.target.value, 10))}
                className="w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value={1}>Last 24 hours</option>
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
              </select>
              <select
                value={maxResults}
                onChange={(e) => setMaxResults(parseInt(e.target.value, 10))}
                className="w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value={5}>Top 5</option>
                <option value={10}>Top 10</option>
                <option value={15}>Top 15</option>
                <option value={20}>Top 20</option>
              </select>
              <button
                onClick={() => handleSearch()}
                disabled={loading}
                className="w-full sm:w-auto inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
              >
                {loading ? (
                  <Loader className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Search className="h-4 w-4 mr-2" />
                )}
                Search
              </button>
              <button
                onClick={() => handleSearch({ forceFresh: true })}
                disabled={loading || !searchTerm.trim()}
                className="w-full sm:w-auto inline-flex items-center justify-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                title="Ignore cache and fetch fresh results"
              >
                <Zap className="h-4 w-4 mr-1" />
                Refresh
              </button>
            </div>
          </div>

          {!selectedArticle && (
            <p className="mt-2 text-xs text-gray-500">Tip: press Enter to search, Cmd/Ctrl + K to jump to search.</p>
          )}

          {recentSearches.length > 0 && !selectedArticle && (
            <div className="mt-3 flex items-center gap-2 flex-wrap">
              <Clock3 className="h-4 w-4 text-gray-500" />
              {recentSearches.map((term) => (
                <button
                  key={term}
                  onClick={() => quickAreaSearch(term)}
                  className="px-2.5 py-1 rounded-full border border-gray-200 text-xs text-gray-700 hover:bg-gray-100"
                >
                  {term}
                </button>
              ))}
            </div>
          )}

          {!selectedArticle && (
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium text-gray-700">Use Case:</span>
              <div className="flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => handleUseCaseToggle('clinical')}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    useCase === 'clinical'
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Clinical
                </button>
                <button
                  onClick={() => handleUseCaseToggle('exploratory')}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    useCase === 'exploratory'
                      ? 'bg-purple-600 text-white shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Exploratory
                </button>
              </div>
            </div>
          )}

          {!selectedArticle && (
            <div className="mt-3 flex items-center gap-4 flex-wrap">
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="searchMode"
                    value="local"
                    checked={searchMode === 'local'}
                    onChange={(e) => setSearchMode(e.target.value)}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700 flex items-center">
                    <Database className="h-4 w-4 mr-1" />
                    Local-style
                  </span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="searchMode"
                    value="pubmed"
                    checked={searchMode === 'pubmed'}
                    onChange={(e) => setSearchMode(e.target.value)}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700 flex items-center">
                    <Globe className="h-4 w-4 mr-1" />
                    PubMed Search
                  </span>
                </label>
              </div>
              <div className="text-xs text-gray-500">{searchStatus}</div>
            </div>
          )}
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4 m-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
                <div className="ml-auto pl-3 flex items-center gap-2">
                  <button
                    onClick={() => handleSearch({ forceFresh: true })}
                    className="text-xs px-2 py-1 rounded border border-red-200 text-red-700 hover:bg-red-100"
                    disabled={loading || !searchTerm.trim()}
                  >
                    Retry
                  </button>
                  <button
                    onClick={() => setError('')}
                    className="text-red-400 hover:text-red-600"
                  >
                    <span className="sr-only">Dismiss</span>
                    <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          )}

          {loading && (
            <div className="text-center p-6">
              <p className="text-sm text-gray-600 mb-4">{searchStatus}</p>
              {searchProgress > 0 ? (
                <div className="w-full max-w-md mx-auto">
                  <div className="bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-primary-600 h-3 rounded-full transition-all duration-300"
                      style={{ width: `${searchProgress}%` }}
                    ></div>
                  </div>
                  <p className="text-sm text-gray-700 mt-2 font-medium">{Math.round(searchProgress)}% complete</p>
                </div>
              ) : (
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
              )}
            </div>
          )}

          {selectedArticle ? (
            <ArticleDetail
              article={selectedArticle}
              onBack={() => setSelectedArticle(null)}
              useCase={useCase}
            />
          ) : (
            <ArticleList
              articles={articles}
              loading={false}
              onArticleSelect={setSelectedArticle}
              onSaveArticle={null}
              useCase={useCase}
              hasSearched={hasSearched}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
