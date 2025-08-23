import React from 'react';
import { Info, Award, Users, Clock, BookOpen } from 'lucide-react';

function ReliabilityBadge({ 
  reliability_score, 
  reliability_band, 
  reliability_reasons, 
  uncertainty, 
  use_case = 'Clinical',
  compact = false,
  onExplainScoring
}) {
  // Don't render if no reliability data
  if (!reliability_score || !reliability_band) {
    return null;
  }

  const getBandColor = (band) => {
    switch (band?.toLowerCase()) {
      case 'high':
        return 'bg-blue-700 text-white';
      case 'moderate':
        return 'bg-sky-500 text-white';
      case 'exploratory':
        return 'bg-orange-400 text-white';
      case 'low':
        return 'bg-gray-400 text-white';
      default:
        return 'bg-gray-400 text-white';
    }
  };

  const getBandIcon = (band) => {
    switch (band?.toLowerCase()) {
      case 'high':
        return <Award className="h-3 w-3" />;
      case 'moderate':
        return <Users className="h-3 w-3" />;
      case 'exploratory':
        return <BookOpen className="h-3 w-3" />;
      case 'low':
        return <Clock className="h-3 w-3" />;
      default:
        return <Info className="h-3 w-3" />;
    }
  };

  if (compact) {
    return (
      <div className="inline-flex items-center space-x-2">
        <span 
          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getBandColor(reliability_band)}`}
        >
          {getBandIcon(reliability_band)}
          <span className="ml-1">{Math.round(reliability_score * 100)}%</span>
        </span>
        {onExplainScoring && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onExplainScoring();
            }}
            className="p-1 text-gray-400 hover:text-blue-600 transition-colors"
            title="Learn about TA-aware reliability scoring"
          >
            <Info className="h-3 w-3" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-2">
      <span 
        className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium ${getBandColor(reliability_band)}`}
      >
        {getBandIcon(reliability_band)}
        <span className="ml-1.5">
          {reliability_band?.charAt(0).toUpperCase() + reliability_band?.slice(1)} Reliability ({Math.round(reliability_score * 100)}%)
        </span>
      </span>
      
      {onExplainScoring && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onExplainScoring();
          }}
          className="p-1 text-gray-400 hover:text-blue-600 transition-colors"
          title="Learn about TA-aware reliability scoring"
        >
          <Info className="h-4 w-4" />
        </button>
      )}
      
      {uncertainty && (
        <div className="text-xs text-gray-500">
          {use_case?.charAt(0).toUpperCase() + use_case?.slice(1)} • {uncertainty} confidence
        </div>
      )}
    </div>
  );
}

export default ReliabilityBadge;
