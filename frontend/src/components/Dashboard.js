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

  // Therapeutic areas for demo
  const therapeuticAreas = [
    'Oncology',
    'Cardiovascular',
    'Neurology',
    'Immunology',
    'Rare Diseases',
    'Infectious Diseases'
  ];

  useEffect(() => {
    loadRecentArticles();
    // eslint-disable-next-line
  }, []);

  const loadRecentArticles = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/articles/recent', {
        params: { days_back: daysBack }
      });
      setArticles(response.data);
    } catch (error) {
      console.error('[Dashboard] Error loading articles:', error);
    }
    setLoading(false);
  };

  const handleSearch = async () => {
    if (!searchTerm.trim()) return;
    setLoading(true);
    setSearchStatus('Searching local database...');
    
    try {
      const endpoint = searchMode === 'pubmed' ? '/articles/search-pubmed' : '/articles/search';
      
      if (searchMode === 'pubmed') {
        setSearchStatus('Searching PubMed (this may take 30+ seconds)...');
      } else {
        setSearchStatus('Searching local database and PubMed if needed...');
      }
      
      const response = await axios.post(endpoint, {
        therapeutic_area: searchTerm,
        days_back: daysBack
      });
      setArticles(response.data);
      setSearchStatus('');
    } catch (error) {
      console.error('[Dashboard] Error searching articles:', error);
      setSearchStatus('Search failed');
    }
    setLoading(false);
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
          {/* Search Mode Toggle */}
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
        </div>
        {/* Content Area */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {loading && (
            <div className="text-center p-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-2"></div>
              <p className="text-sm text-gray-600">{searchStatus}</p>
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
              loading={loading}
              onArticleSelect={setSelectedArticle}
              onSaveArticle={handleSaveArticle}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard; 