import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Search, 
  Loader,
  Database,
  Globe
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
  const [searchMode, setSearchMode] = useState('local'); // 'local' or 'pubmed'
  const [showTutorial, setShowTutorial] = useState(() => {
    return localStorage.getItem('msl_tutorial_complete') !== 'true';
  });
  const [searchStatus, setSearchStatus] = useState('');
  const [searchProgress, setSearchProgress] = useState(0);
  const [useCase, setUseCase] = useState('clinical'); // 'clinical' or 'exploratory'
  const [error, setError] = useState(''); // Error state for user feedback

  useEffect(() => {
    loadRecentArticles();
    // eslint-disable-next-line
  }, []);

  const loadRecentArticles = async () => {
    setLoading(true);
    setError(''); // Clear error on new load
    try {
      const response = await axios.get('/articles/recent', {
        params: { days_back: daysBack }
      });
      setArticles(response.data);
    } catch (error) {
      console.error('[Dashboard] Error loading articles:', error);
      setError('Failed to load recent articles. Please check your connection and try again.');
    }
    setLoading(false);
  };

  const handleSearch = async () => {
    if (!searchTerm.trim()) return;
    setLoading(true);
    setSearchProgress(0);
    setError(''); // Clear error on new search
    
    try {
      const endpoint = searchMode === 'pubmed' ? '/articles/search-pubmed' : '/articles/search';
      
      if (searchMode === 'pubmed') {
        setSearchStatus('Searching PubMed (this may take 15+ seconds)...');
        
        // Show progress animation
        const progressInterval = setInterval(() => {
          setSearchProgress(prev => {
            if (prev >= 90) return prev;
            return prev + Math.random() * 10;
          });
        }, 500);
        
        const response = await axios.post(endpoint, {
          therapeutic_area: searchTerm,
          days_back: daysBack,
          use_case: useCase
        });
        
        clearInterval(progressInterval);
        setSearchProgress(100);
        setArticles(response.data);
        setSearchStatus('');
      } else {
        setSearchStatus('Searching local database...');
        const response = await axios.post(endpoint, {
          therapeutic_area: searchTerm,
          days_back: daysBack,
          use_case: useCase
        });
        setArticles(response.data);
        setSearchStatus('');
      }
    } catch (error) {
      console.error('[Dashboard] Error searching articles:', error);
      setError(`Search failed: ${error.response?.data?.detail || error.message || 'Unknown error'}. Please try again.`);
      setSearchStatus('');
    }
    setLoading(false);
    setSearchProgress(0);
  };

  const handleSaveArticle = async (article) => {
    try {
      await axios.post('/articles/fetch-pubmed', {
        therapeutic_area: article.therapeutic_area || searchTerm,
        days_back: daysBack
      });
      loadRecentArticles();
    } catch (error) {
      console.error('[Dashboard] Error saving article:', error);
    }
  };

  const handleTutorialClose = () => {
    setShowTutorial(false);
    localStorage.setItem('msl_tutorial_complete', 'true');
  };

  const handleTutorialOpen = () => {
    setShowTutorial(true);
  };


  const handleUseCaseToggle = async (newUseCase) => {
    console.log(`🎯 Toggle clicked: ${newUseCase}`);
    setUseCase(newUseCase);
    
    // Re-search if we have articles and a search term, regardless of search mode
    if (articles.length > 0 && searchTerm) {
      setLoading(true);
      setArticles([]); // Clear articles first
      setError('');
      
      try {
        console.log(`🔄 Re-searching with use case: ${newUseCase}`);
        const endpoint = searchMode === 'pubmed' ? '/articles/search-pubmed' : '/articles/search';
        const response = await axios.post(endpoint, {
          therapeutic_area: searchTerm,
          days_back: daysBack,
          use_case: newUseCase
        });
        
        // Force a complete re-render by creating a new array
        setArticles([...response.data]);
        console.log(`✅ Updated with ${response.data.length} articles for ${newUseCase} use case`);
      } catch (error) {
        console.error('Error re-ranking articles:', error);
        setError(`Failed to update articles for ${newUseCase} use case. Please try searching again.`);
      }
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex bg-gray-50">
      {/* Tutorial Modal */}
      <TutorialModal open={showTutorial} onClose={handleTutorialClose} />
      {/* '?' Button - bottom right, floating, unobtrusive */}
      <button
        onClick={handleTutorialOpen}
        className="fixed bottom-6 right-6 z-40 bg-primary-600 text-white rounded-full w-12 h-12 flex items-center justify-center shadow-lg hover:bg-primary-700 focus:outline-none"
        title="Show tutorial"
        style={{ fontSize: 28, fontWeight: 'bold' }}
        aria-label="Show tutorial"
      >
        ?
      </button>
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Search Section */}
        <div className="bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Search by therapeutic area (e.g., Oncology, Cardiovascular)..."
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <select
                value={daysBack}
                onChange={(e) => setDaysBack(parseInt(e.target.value))}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value={1}>Last 24 hours</option>
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
              </select>
              <button
                onClick={handleSearch}
                disabled={loading}
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
          {/* Conditional toggles - only show when not viewing article detail */}
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
          {/* Search Mode Toggle */}
          {!selectedArticle && (
            <div className="mt-3 flex items-center gap-4">
              <div className="flex items-center space-x-4">
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
                    Local Database
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
            </div>
          )}
        </div>
        {/* Content Area */}
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
                <div className="ml-auto pl-3">
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
              {searchMode === 'pubmed' && searchProgress > 0 ? (
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
            />
          ) : (
            <ArticleList 
              articles={articles}
              loading={false} // Set to false to prevent duplicate spinners
              onArticleSelect={setSelectedArticle}
              onSaveArticle={handleSaveArticle}
              useCase={useCase} // Pass dynamic useCase
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard; 