import React, { useState } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { ArrowLeft, ExternalLink, Brain, Calendar, User, Loader } from 'lucide-react';

// Impact Factor Badge Component (same as in ArticleList)
function ImpactFactorBadge({ impactFactor, reliabilityTier }) {
  const getImpactFactorColor = (impactFactor) => {
    if (impactFactor >= 50) {
      return 'bg-blue-700 text-white'; // Tier 1: Royal blue - Highest reliability
    } else if (impactFactor >= 10) {
      return 'bg-sky-500 text-white'; // Tier 2: Sky blue - High reliability
    } else if (impactFactor >= 5) {
      return 'bg-orange-400 text-white'; // Tier 3: Coral - Good reliability
    } else if (impactFactor >= 2) {
      return 'bg-gray-400 text-white'; // Tier 4: Silver - Standard reliability
    } else {
      return null; // No color for lower reliability - keep it simple
    }
  };

  // Don't show badge for unknown/low impact factor
  if (!impactFactor || impactFactor < 2) {
    return null;
  }

  const colorClass = getImpactFactorColor(impactFactor);
  if (!colorClass) return null;

  return (
    <div className="inline-flex items-center space-x-1">
      <span 
        className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium ${colorClass}`}
        title={reliabilityTier || 'Journal Impact Factor'}
      >
        Impact Factor: {impactFactor.toFixed(1)}
      </span>
    </div>
  );
}

function ArticleDetail({ article, onBack }) {
  const [insights, setInsights] = useState(null);
  const [loadingInsights, setLoadingInsights] = useState(false);

  const generateInsights = async () => {
    setLoadingInsights(true);
    try {
      const response = await axios.post(`/articles/${article.pubmed_id}/insights`, {});
      setInsights(response.data.insights);
    } catch (error) {
      console.error('Error generating insights:', error);
      setInsights('Error generating insights. Please try again.');
    }
    setLoadingInsights(false);
  };

  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      <div className="max-w-4xl mx-auto p-6">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={onBack}
            className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to articles
          </button>
          
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex justify-between items-start mb-4">
              <h1 className="text-2xl font-bold text-gray-900 pr-4">
                {article.title}
              </h1>
              <button
                onClick={() => window.open(article.link, '_blank')}
                className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600"
                title="Open in PubMed"
              >
                <ExternalLink className="h-5 w-5" />
              </button>
            </div>
            
            <div className="flex flex-wrap items-center text-sm text-gray-500 mb-4 space-x-6">
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
              <div className="flex items-center justify-between text-sm text-gray-600 mb-4">
                <div>
                  <span className="font-medium">Journal:</span> {article.journal}
                </div>
                <ImpactFactorBadge 
                  impactFactor={article.impact_factor} 
                  reliabilityTier={article.reliability_tier}
                />
              </div>
            )}
            
            {article.therapeutic_area && (
              <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-primary-100 text-primary-800 mb-4">
                {article.therapeutic_area}
              </div>
            )}
            
            <div className="text-sm text-gray-500 mb-4">
              <span className="font-medium">PubMed ID:</span> {article.pubmed_id}
            </div>
            
            <div className="prose max-w-none">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Abstract</h3>
              <p className="text-gray-700 leading-relaxed">
                {article.abstract || 'No abstract available.'}
              </p>
            </div>
          </div>
        </div>

        {/* AI Insights Section */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center">
              <Brain className="h-5 w-5 mr-2 text-primary-600" />
              Medical Affairs Insights
            </h2>
            <button
              onClick={generateInsights}
              disabled={loadingInsights}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
            >
              {loadingInsights ? (
                <>
                  <Loader className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Brain className="h-4 w-4 mr-2" />
                  Generate Insights
                </>
              )}
            </button>
          </div>
          
          {insights && (
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown 
                  components={{
                    h1: ({node, ...props}) => <h1 className="text-xl font-bold text-gray-900 mb-3" {...props} />,
                    h2: ({node, ...props}) => <h2 className="text-lg font-semibold text-gray-900 mb-2 mt-4" {...props} />,
                    h3: ({node, ...props}) => <h3 className="text-base font-medium text-gray-900 mb-2 mt-3" {...props} />,
                    p: ({node, ...props}) => <p className="mb-3 text-gray-700 leading-relaxed" {...props} />,
                    ul: ({node, ...props}) => <ul className="list-disc list-inside mb-3 space-y-1" {...props} />,
                    ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-3 space-y-1" {...props} />,
                    li: ({node, ...props}) => <li className="text-gray-700" {...props} />,
                    strong: ({node, ...props}) => <strong className="font-semibold text-gray-900" {...props} />,
                    em: ({node, ...props}) => <em className="italic text-gray-800" {...props} />,
                  }}
                >
                  {insights}
                </ReactMarkdown>
              </div>
            </div>
          )}
          
          {!insights && !loadingInsights && (
            <div className="text-center py-8 text-gray-500">
              <Brain className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Click "Generate Insights" to get AI-powered analysis of this research.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ArticleDetail; 