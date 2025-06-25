import React from 'react';
import { ExternalLink, Calendar, User, Brain, Save } from 'lucide-react';

function ArticleList({ articles, loading, onArticleSelect, onSaveArticle }) {
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
        <h3 className="text-lg font-medium">No articles found</h3>
        <p className="text-sm">Try adjusting your search criteria or time range.</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          {articles.length} article{articles.length !== 1 ? 's' : ''} found
        </h2>
      </div>
      
      <div className="space-y-4">
        {articles.map((article) => (
          <div
            key={article.id || article.pubmed_id}
            className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => onArticleSelect(article)}
          >
            <div className="flex justify-between items-start mb-3">
              <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
                {article.title}
              </h3>
              <div className="flex items-center space-x-2">
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
                    window.open(article.link, '_blank');
                  }}
                  className="p-1 text-gray-400 hover:text-gray-600"
                  title="Open in PubMed"
                >
                  <ExternalLink className="h-4 w-4" />
                </button>
              </div>
            </div>
            
            <div className="flex items-center text-sm text-gray-500 mb-3 space-x-4">
              <div className="flex items-center">
                <User className="h-4 w-4 mr-1" />
                <span>{article.authors?.join(', ') || 'Unknown authors'}</span>
              </div>
              <div className="flex items-center">
                <Calendar className="h-4 w-4 mr-1" />
                <span>{article.publication_date}</span>
              </div>
            </div>
            
            {article.journal && (
              <div className="text-sm text-gray-600 mb-3">
                <span className="font-medium">Journal:</span> {article.journal}
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
            
            <div className="mt-4 flex justify-between items-center">
              <span className="text-xs text-gray-500">
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
    </div>
  );
}

export default ArticleList; 