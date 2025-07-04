import React from 'react';
import { ExternalLink, Calendar, User, Flask, Target, Building } from 'lucide-react';

function TrialList({ trials, loading, onTrialSelect }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (trials.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <Flask className="h-16 w-16 mb-4" />
        <h3 className="text-lg font-medium">No clinical trials found</h3>
        <p className="text-sm">Try adjusting your search criteria.</p>
      </div>
    );
  }

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'recruiting':
        return 'text-green-600 bg-green-100';
      case 'completed':
        return 'text-blue-600 bg-blue-100';
      case 'terminated':
        return 'text-red-600 bg-red-100';
      case 'suspended':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getPhaseColor = (phase) => {
    if (phase?.toLowerCase().includes('phase 1')) return 'text-purple-600 bg-purple-100';
    if (phase?.toLowerCase().includes('phase 2')) return 'text-blue-600 bg-blue-100';
    if (phase?.toLowerCase().includes('phase 3')) return 'text-green-600 bg-green-100';
    if (phase?.toLowerCase().includes('phase 4')) return 'text-orange-600 bg-orange-100';
    return 'text-gray-600 bg-gray-100';
  };

  return (
    <div className="p-6 h-full max-h-full overflow-y-auto">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          {trials.length} clinical trial{trials.length !== 1 ? 's' : ''} found
        </h2>
      </div>
      
      <div className="space-y-4">
        {trials.map((trial) => (
          <div
            key={trial.nct_id}
            className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => onTrialSelect(trial)}
          >
            <div className="flex justify-between items-start mb-3">
              <h3 className="text-lg font-semibold text-gray-900 line-clamp-2 pr-4">
                {trial.title}
              </h3>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  window.open(trial.link, '_blank');
                }}
                className="p-1 text-gray-400 hover:text-gray-600"
                title="Open in ClinicalTrials.gov"
              >
                <ExternalLink className="h-4 w-4" />
              </button>
            </div>
            
            <div className="flex items-center text-sm text-gray-500 mb-3 space-x-4">
              <div className="flex items-center">
                <Target className="h-4 w-4 mr-1" />
                <span className="font-medium">NCT ID:</span> {trial.nct_id}
              </div>
              <div className="flex items-center">
                <Building className="h-4 w-4 mr-1" />
                <span>{trial.sponsor}</span>
              </div>
            </div>
            
            {trial.condition && (
              <div className="text-sm text-gray-600 mb-3">
                <span className="font-medium">Condition:</span> {trial.condition}
              </div>
            )}
            
            {trial.intervention && (
              <div className="text-sm text-gray-600 mb-3">
                <span className="font-medium">Intervention:</span> {trial.intervention}
              </div>
            )}
            
            <div className="flex flex-wrap gap-2 mb-3">
              {trial.status && (
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(trial.status)}`}>
                  {trial.status}
                </span>
              )}
              {trial.phase && (
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPhaseColor(trial.phase)}`}>
                  {trial.phase}
                </span>
              )}
              {trial.study_type && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                  {trial.study_type}
                </span>
              )}
            </div>
            
            <div className="flex items-center text-sm text-gray-500 mb-3 space-x-4">
              {trial.start_date && (
                <div className="flex items-center">
                  <Calendar className="h-4 w-4 mr-1" />
                  <span>Started: {trial.start_date}</span>
                </div>
              )}
              {trial.completion_date && (
                <div className="flex items-center">
                  <Calendar className="h-4 w-4 mr-1" />
                  <span>Completed: {trial.completion_date}</span>
                </div>
              )}
              {trial.enrollment && (
                <div className="flex items-center">
                  <User className="h-4 w-4 mr-1" />
                  <span>Enrollment: {trial.enrollment}</span>
                </div>
              )}
            </div>
            
            <div className="mt-4 flex justify-between items-center">
              <span className="text-xs text-gray-500">
                Source: {trial.source}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onTrialSelect(trial);
                }}
                className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-primary-700 bg-primary-100 hover:bg-primary-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <Flask className="h-3 w-3 mr-1" />
                View Details
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default TrialList; 