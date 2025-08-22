import React, { useState } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { ArrowLeft, ExternalLink, Brain, Calendar, User, Loader } from 'lucide-react';
import ReliabilityBadge from './ReliabilityBadge';
import ScoringExplanationModal from './ScoringExplanationModal';

function ArticleDetail({ article, onBack }) {
  const [insights, setInsights] = useState(null);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [showScoringModal, setShowScoringModal] = useState(false);

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
                <ReliabilityBadge 
                  reliability_score={article.reliability_score}
                  reliability_band={article.reliability_band}
                  reliability_reasons={article.reliability_reasons}
                  uncertainty={article.uncertainty}
                  use_case="Clinical"
                  compact={false}
                  onExplainScoring={() => setShowScoringModal(true)}
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
                    h1: ({children, ...props}) => <h1 className="text-xl font-bold text-gray-900 mb-3" {...props}>{children}</h1>,
                    h2: ({children, ...props}) => <h2 className="text-lg font-semibold text-gray-900 mb-2 mt-4" {...props}>{children}</h2>,
                    h3: ({children, ...props}) => <h3 className="text-base font-medium text-gray-900 mb-2 mt-3" {...props}>{children}</h3>,
                    p: ({children, ...props}) => <p className="mb-3 text-gray-700 leading-relaxed" {...props}>{children}</p>,
                    ul: ({children, ...props}) => <ul className="list-disc list-inside mb-3 space-y-1" {...props}>{children}</ul>,
                    ol: ({children, ...props}) => <ol className="list-decimal list-inside mb-3 space-y-1" {...props}>{children}</ol>,
                    li: ({children, ...props}) => <li className="text-gray-700" {...props}>{children}</li>,
                    strong: ({children, ...props}) => <strong className="font-semibold text-gray-900" {...props}>{children}</strong>,
                    em: ({children, ...props}) => <em className="italic text-gray-800" {...props}>{children}</em>,
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
      
      <ScoringExplanationModal 
        open={showScoringModal}
        onClose={() => setShowScoringModal(false)}
      />
    </div>
  );
}

export default ArticleDetail; 