import React from 'react';
import { ArrowLeft, ExternalLink, Calendar, User, Flask, Target, Building, MapPin } from 'lucide-react';

function TrialDetail({ trial, onBack }) {
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
    <div className="h-full overflow-y-auto bg-gray-50">
      <div className="max-w-4xl mx-auto p-6">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={onBack}
            className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to trials
          </button>
          
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex justify-between items-start mb-4">
              <h1 className="text-2xl font-bold text-gray-900 pr-4">
                {trial.title}
              </h1>
              <button
                onClick={() => window.open(trial.link, '_blank')}
                className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600"
                title="Open in ClinicalTrials.gov"
              >
                <ExternalLink className="h-5 w-5" />
              </button>
            </div>
            
            <div className="flex items-center text-sm text-gray-500 mb-4 space-x-6">
              <div className="flex items-center">
                <Target className="h-4 w-4 mr-1" />
                <span className="font-medium">NCT ID:</span> {trial.nct_id}
              </div>
              <div className="flex items-center">
                <Building className="h-4 w-4 mr-1" />
                <span>{trial.sponsor}</span>
              </div>
            </div>
            
            <div className="flex flex-wrap gap-2 mb-4">
              {trial.status && (
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(trial.status)}`}>
                  {trial.status}
                </span>
              )}
              {trial.phase && (
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getPhaseColor(trial.phase)}`}>
                  {trial.phase}
                </span>
              )}
              {trial.study_type && (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
                  {trial.study_type}
                </span>
              )}
            </div>
            
            <div className="flex flex-wrap items-center text-sm text-gray-500 mb-4 space-x-6">
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
          </div>
        </div>

        {/* Trial Details */}
        <div className="space-y-6">
          {trial.condition && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Condition</h2>
              <p className="text-gray-700">{trial.condition}</p>
            </div>
          )}
          
          {trial.intervention && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Intervention</h2>
              <p className="text-gray-700">{trial.intervention}</p>
            </div>
          )}
          
          {trial.description && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Description</h2>
              <div className="prose max-w-none">
                <p className="text-gray-700 leading-relaxed">
                  {trial.description}
                </p>
              </div>
            </div>
          )}
          
          {trial.study_design && Object.keys(trial.study_design).length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Study Design</h2>
              <div className="space-y-2">
                {Object.entries(trial.study_design).map(([key, value]) => (
                  <div key={key} className="flex">
                    <span className="font-medium text-gray-700 w-32">{key}:</span>
                    <span className="text-gray-600">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Trial Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <span className="font-medium text-gray-700">Sponsor:</span>
                <p className="text-gray-600">{trial.sponsor}</p>
              </div>
              {trial.sponsor_class && (
                <div>
                  <span className="font-medium text-gray-700">Sponsor Type:</span>
                  <p className="text-gray-600">{trial.sponsor_class}</p>
                </div>
              )}
              <div>
                <span className="font-medium text-gray-700">Source:</span>
                <p className="text-gray-600">{trial.source}</p>
              </div>
              <div>
                <span className="font-medium text-gray-700">NCT ID:</span>
                <p className="text-gray-600">{trial.nct_id}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TrialDetail; 