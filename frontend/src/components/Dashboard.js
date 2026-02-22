import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Search,
  Loader,
  Globe,
  Zap
} from 'lucide-react';
import ArticleList from './ArticleList';
import ArticleDetail from './ArticleDetail';
import TutorialModal from './TutorialModal';

function Dashboard() {
  const [articles, setArticles] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [daysBack, setDaysBack] = useState(7);
  const [loading, setLoading] = useState(false);
  const [searchMode, setSearchMode] = useState('pubmed');
  const [showTutorial, setShowTutorial] = useState(() => {
    return localStorage.getItem('msl_tutorial_complete') !== 'true';
  });
  const [searchStatus, setSearchStatus] = useState('');
  const [searchProgress, setSearchProgress] = useState(0);
  const [useCase, setUseCase] = useState('clinical');
  const [error, setError] = useState('');
  const [hasSearched, setHasSearched] = useState(false);

  const searchCacheRef = useRef(new Map());
  const inFlightControllerRef = useRef(null);
  const progressIntervalRef = useRef(null);
  const searchInputRef = useRef(null);

  const buildSearchKey = useCallback((params) => {
    return JSON.stringify({
      therapeutic_area: params.therapeutic_area.trim().toLowerCase(),
      days_back: params.days_back,
      use_case: params.use_case,
      search_mode: params.search_mode,
    });
  }, []);

  const clearProgressTimer = useCallback(() => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    const handleGlobalShortcut = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleGlobalShortcut);
    return () => window.removeEventListener('keydown', handleGlobalShortcut);
  }, []);

  useEffect(() => {
    return () => {
      clearProgressTimer();
      inFlightControllerRef.current?.abort();
    };
  }, [clearProgressTimer]);

  const runSearch = useCallback(async ({ therapeutic_area, days_back, use_case, search_mode }, { force = false } = {}) => {
    const normalizedTerm = therapeutic_area.trim();
    if (!normalizedTerm) return;

    setError('');
    setSearchStatus('');
    setHasSearched(true);

    const key = buildSearchKey({ therapeutic_area: normalizedTerm, days_back, use_case, search_mode });

    if (!force && searchCacheRef.current.has(key)) {
      setArticles(searchCacheRef.current.get(key));
      setSearchStatus('Loaded from recent search');
      setTimeout(() => setSearchStatus(''), 1200);
      return;
    }

    inFlightControllerRef.current?.abort();
    clearProgressTimer();

    const controller = new AbortController();
    inFlightControllerRef.current = controller;

    setLoading(true);
    setSearchProgress(0);

    try {
      const endpoint = search_mode === 'pubmed' ? '/articles/search-pubmed' : '/articles/search';

      if (search_mode === 'pubmed') {
        setSearchStatus('Searching PubMed (usually 10–20s)...');
        progressIntervalRef.current = setInterval(() => {
          setSearchProgress((prev) => (prev >= 92 ? prev : prev + Math.random() * 8));
        }, 450);
      } else {
        setSearchStatus('Searching local database...');
      }

      const response = await axios.post(
        endpoint,
        {
          therapeutic_area: normalizedTerm,
          days_back,
          use_case,
        },
        { signal: controller.signal }
      );

      clearProgressTimer();
      setSearchProgress(100);

      const payload = Array.isArray(response.data) ? response.data : [];
      searchCacheRef.current.set(key, payload);
      setArticles(payload);
      setSelectedArticle(null);
      setSearchStatus('');
    } catch (err) {
      clearProgressTimer();

      if (err?.code === 'ERR_CANCELED' || axios.isCancel?.(err)) {
        return;
      }

      if (search_mode === 'local' && err?.response?.status === 404) {
        setSearchMode('pubmed');
        setSearchStatus('Local search unavailable. Switching to PubMed...');
        await runSearch({ therapeutic_area: normalizedTerm, days_back, use_case, search_mode: 'pubmed' }, { force: true });
        return;
      }

      console.error('[Dashboard] Error searching articles:', err);
      setError(`Search failed: ${err.response?.data?.detail || err.message || 'Unknown error'}. Please try again.`);
      setSearchStatus('');
    } finally {
      setLoading(false);
      setSearchProgress(0);
      inFlightControllerRef.current = null;
    }
  }, [buildSearchKey, clearProgressTimer]);

  const handleSearch = useCallback(() => {
    runSearch({
      therapeutic_area: searchTerm,
      days_back: daysBack,
      use_case: useCase,
      search_mode: searchMode,
    });
  }, [runSearch, searchTerm, daysBack, useCase, searchMode]);

  const handleTutorialClose = () => {
    setShowTutorial(false);
    localStorage.setItem('msl_tutorial_complete', 'true');
  };

  const handleTutorialOpen = () => {
    setShowTutorial(true);
  };

  const handleUseCaseToggle = (newUseCase) => {
    setUseCase(newUseCase);

    if (searchTerm.trim()) {
      runSearch({
        therapeutic_area: searchTerm,
        days_back: daysBack,
        use_case: newUseCase,
        search_mode: searchMode,
      });
    }
  };

  return (
    <div className="h-screen flex bg-gray-50">
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
        <div className="bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8 py-4">
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
                  placeholder="Search by therapeutic area (e.g., Oncology, Cardiovascular)..."
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                />
              </div>
              <p className="text-xs text-gray-500 mt-1 flex items-center">
                <Zap className="h-3 w-3 mr-1" />
                Press Enter to search • Ctrl/Cmd+K to focus
              </p>
            </div>
            <div className="flex gap-2">
              <select
                value={daysBack}
                onChange={(e) => setDaysBack(parseInt(e.target.value, 10))}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value={1}>Last 24 hours</option>
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
              </select>
              <button
                onClick={handleSearch}
                disabled={loading || !searchTerm.trim()}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
              >
                {loading ? (
                  <Loader className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Search className="h-4 w-4 mr-2" />
                )}
                Search
              </button>
            </div>
          </div>

          {!selectedArticle && (
            <div className="mt-3 flex items-center space-x-4">
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
            <div className="mt-3 flex items-center gap-4">
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
                    onClick={handleSearch}
                    className="text-xs px-2 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200"
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
              <p className="text-sm text-gray-600 mb-4">{searchStatus || 'Searching...'}</p>
              <div className="w-full max-w-md mx-auto">
                <div className="bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-primary-600 h-3 rounded-full transition-all duration-300"
                    style={{ width: `${searchProgress || 8}%` }}
                  />
                </div>
                <p className="text-sm text-gray-700 mt-2 font-medium">{Math.round(searchProgress)}% complete</p>
              </div>
            </div>
          )}

          {!loading && searchStatus && (
            <p className="text-center text-xs text-gray-500 py-2">{searchStatus}</p>
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
