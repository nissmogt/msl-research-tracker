import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Search, 
  Loader,
  Database,
  Globe,
  Flask,
  FileText,
  Bell,
  Star,
  TrendingUp,
  Users
} from 'lucide-react';
import ArticleList from './ArticleList';
import ArticleDetail from './ArticleDetail';
import TrialList from './TrialList';
import TrialDetail from './TrialDetail';
import TutorialModal from './TutorialModal';
// import TATreeSelect from './TATreeSelect';

function Dashboard() {
  const [articles, setArticles] = useState([]);
  const [trials, setTrials] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [selectedTrial, setSelectedTrial] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [daysBack, setDaysBack] = useState(7);
  const [loading, setLoading] = useState(false);
  const [searchMode, setSearchMode] = useState('local'); // 'local' or 'pubmed'
  const [contentType, setContentType] = useState('articles'); // 'articles' or 'trials'
  const [showTutorial, setShowTutorial] = useState(() => {
    return localStorage.getItem('msl_tutorial_complete') !== 'true';
  });
  const [showAnnouncements, setShowAnnouncements] = useState(true);

  // Announcements data
  const announcements = [
    {
      id: 1,
      type: 'feature',
      title: '🎉 New Clinical Trials Integration',
      content: 'Search and explore clinical trials directly from ClinicalTrials.gov. Get detailed trial information including phases, enrollment status, and study designs.',
      icon: Flask,
      color: 'lapis'
    },
    {
      id: 2,
      type: 'update',
      title: '📊 Enhanced Article Analysis',
      content: 'Improved article filtering and analysis with better therapeutic area detection and abstract quality assessment.',
      icon: TrendingUp,
      color: 'lapis'
    },
    {
      id: 3,
      type: 'tip',
      title: '💡 Pro Tip: Use PubMed Search',
      content: 'Switch to "PubMed Search" mode to find the latest articles that haven\'t been saved to your local database yet.',
      icon: Star,
      color: 'lapis'
    },
    {
      id: 4,
      type: 'community',
      title: '👥 MSL Community Features',
      content: 'Coming soon: Share insights, collaborate with other MSLs, and build a knowledge network across therapeutic areas.',
      icon: Users,
      color: 'lapis'
    }
  ];

  useEffect(() => {
    if (contentType === 'articles') {
      loadRecentArticles();
    }
    // eslint-disable-next-line
  }, [contentType]);

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
    try {
      if (contentType === 'articles') {
        const endpoint = searchMode === 'pubmed' ? '/articles/search-pubmed' : '/articles/search';
        const response = await axios.post(endpoint, {
          therapeutic_area: searchTerm,
          days_back: daysBack
        });
        setArticles(response.data);
      } else {
        // Search trials
        const response = await axios.post('/trials/search', {
          therapeutic_area: searchTerm,
          days_back: daysBack
        });
        setTrials(response.data);
      }
    } catch (error) {
      console.error('[Dashboard] Error searching:', error);
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

  const handleContentTypeChange = (type) => {
    setContentType(type);
    setSelectedArticle(null);
    setSelectedTrial(null);
    setArticles([]);
    setTrials([]);
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
                  placeholder={`Search by therapeutic area (e.g., Oncology, Cardiovascular)...`}
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                />
              </div>
            </div>
            <div className="flex gap-2 items-end">
              {contentType === 'articles' && (
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
              )}
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
          
          {/* Content Type Toggle */}
          <div className="mt-3 flex items-center gap-4">
            <div className="flex items-center space-x-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="contentType"
                  value="articles"
                  checked={contentType === 'articles'}
                  onChange={(e) => handleContentTypeChange(e.target.value)}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700 flex items-center">
                  <FileText className="h-4 w-4 mr-1" />
                  Articles
                </span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="contentType"
                  value="trials"
                  checked={contentType === 'trials'}
                  onChange={(e) => handleContentTypeChange(e.target.value)}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700 flex items-center">
                  <Flask className="h-4 w-4 mr-1" />
                  Clinical Trials
                </span>
              </label>
            </div>
            
            {/* Search Mode Toggle - Only show for articles */}
            {contentType === 'articles' && (
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
            )}
          </div>
        </div>
        
        {/* Content Area */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {/* Announcements Section */}
          {showAnnouncements && (
            <div className="bg-gradient-to-r from-lapis-50 to-lapis-100 border-b border-lapis-200 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center">
                  <Bell className="h-5 w-5 text-lapis-600 mr-2" />
                  <h3 className="text-lg font-semibold text-lapis-800">Latest Updates</h3>
                </div>
                <button
                  onClick={() => setShowAnnouncements(false)}
                  className="text-lapis-600 hover:text-lapis-700 text-sm"
                >
                  Dismiss
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {announcements.map((announcement) => {
                  const Icon = announcement.icon;
                  return (
                    <div
                      key={announcement.id}
                      className="bg-white rounded-lg border border-lapis-200 p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start">
                        <div className="flex-shrink-0">
                          <div className="w-8 h-8 bg-lapis-100 rounded-lg flex items-center justify-center">
                            <Icon className="h-4 w-4 text-lapis-600" />
                          </div>
                        </div>
                        <div className="ml-3 flex-1">
                          <h4 className="text-sm font-medium text-lapis-800 mb-1">
                            {announcement.title}
                          </h4>
                          <p className="text-sm text-lapis-700 leading-relaxed">
                            {announcement.content}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          
          {contentType === 'articles' ? (
            selectedArticle ? (
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
            )
          ) : (
            selectedTrial ? (
              <TrialDetail 
                trial={selectedTrial} 
                onBack={() => setSelectedTrial(null)}
              />
            ) : (
              <TrialList 
                trials={trials}
                loading={loading}
                onTrialSelect={setSelectedTrial}
              />
            )
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard; 