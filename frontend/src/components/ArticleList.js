import React, { useState } from 'react';
import { ExternalLink, Calendar, User, Brain, Save } from 'lucide-react';
import ReliabilityBadge from './ReliabilityBadge';
import ScoringExplanationModal from './ScoringExplanationModal';

function ArticleList({ articles, loading, onArticleSelect, onSaveArticle, useCase, hasSearched = false }) {
  const [showScoringModal, setShowScoringModal] = useState(false);

  const formatAuthors = (authors) => {
    if (!Array.isArray(authors) || authors.length === 0) return 'Unknown authors';
    if (authors.length <= 4) return authors.join(', ');
    return `${authors.slice(0, 4).join(', ')} +${authors.length - 4} more`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <Brain className="h-16 w-16 mb-4" />
        <h3 className="text-lg font-medium">{hasSearched ? 'No articles found' : 'Start with a therapeutic area search'}</h3>
        <p className="text-sm">{hasSearched ? 'Try adjusting your search criteria or time range.' : 'Type a therapeutic area and press Enter to get ranked results.'}</p>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 h-full max-h-full overflow-y-auto">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          {articles.length} article{articles.length !== 1 ? 's' : ''} found
        </h2>
      </div>
      
      <div className="space-y-4">
        {articles.map((article) => (
          <div
            key={article.id || article.pubmed_id}
            className="bg-white rounded-lg border border-gray-200 p-4 sm:p-6 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => onArticleSelect(article)}
          >
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 mb-3">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900 line-clamp-2 min-w-0">
                {article.title}
              </h3>
              <div className="flex items-center space-x-2 self-end sm:self-auto">
                {!article.id && onSaveArticle && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSaveArticle(article);
                    }}
                    className="p-1 text-green-600 hover:text-green-700"
                    title="Save to local database"
                  >
                    <Save className="h-4 w-4" />
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    window.open(article.link, '_blank', 'noopener,noreferrer');
                  }}
                  className="p-1 text-gray-400 hover:text-gray-600"
                  title="Open in PubMed"
                >
                  <ExternalLink className="h-4 w-4" />
                </button>
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row sm:items-center text-sm text-gray-500 mb-3 gap-2 sm:gap-4">
              <div className="flex items-center">
                <User className="h-4 w-4 mr-1" />
                <span>{formatAuthors(article.authors)}</span>
              </div>
              <div className="flex items-center">
                <Calendar className="h-4 w-4 mr-1" />
                <span>{article.publication_date}</span>
              </div>
            </div>
            
            {article.journal && (
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between text-sm text-gray-600 mb-3 gap-2">
                <div className="flex items-center space-x-2">
                  <span className="font-medium">Journal:</span> 
                  <span>{article.journal}</span>
                </div>
                <ReliabilityBadge 
                  reliability_score={article.reliability_score}
                  reliability_band={article.reliability_band}
                  reliability_reasons={article.reliability_reasons}
                  uncertainty={article.uncertainty}
                  use_case={useCase || "Clinical"}
                  compact={true}
                  onExplainScoring={() => setShowScoringModal(true)}
                />
              </div>
            )}
            
            {article.therapeutic_area && (
              <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800 mb-3">
                {article.therapeutic_area}
              </div>
            )}
            
            <p className="text-gray-700 text-sm line-clamp-3">
              {article.abstract || 'No abstract available.'}
            </p>
            
            <div className="mt-4 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
              <span className="text-xs text-gray-500 break-all">
                PubMed ID: {article.pubmed_id}
                {!article.id && (
                  <span className="ml-2 text-orange-600">(Not saved locally)</span>
                )}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onArticleSelect(article);
                }}
                className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-primary-700 bg-primary-100 hover:bg-primary-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <Brain className="h-3 w-3 mr-1" />
                View Details
              </button>
            </div>
          </div>
        ))}
      </div>
      
      <ScoringExplanationModal 
        open={showScoringModal}
        onClose={() => setShowScoringModal(false)}
      />
    </div>
  );
}

export default ArticleList; 