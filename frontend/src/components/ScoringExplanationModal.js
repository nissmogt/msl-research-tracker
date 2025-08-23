import React from 'react';
import { X, Award, Target, Clock, BookOpen, Shield } from 'lucide-react';

function ScoringExplanationModal({ open, onClose }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">TA-Aware Reliability Scoring System</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-8">
          {/* Revolutionary Breakthrough */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <div className="flex items-center space-x-2 mb-3">
              <Award className="h-6 w-6 text-blue-600" />
              <h3 className="text-xl font-bold text-blue-900">Therapeutic Area-Aware Impact Factor</h3>
            </div>
            <p className="text-blue-800 mb-3">
              Our TA-aware system solves the "Journal of Clinical Oncology vs Nature in Oncology" problem by recognizing that 
              <strong> specialized journals may rank lower in their domains</strong>.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white rounded p-4 border border-blue-200">
                <div className="text-sm font-medium text-blue-900">Traditional Impact Factor</div>
                <div className="text-blue-700">Nature (64.8) &gt; JCO (37.2)</div>
                <div className="text-xs text-blue-600">❌ Always favors broad journals</div>
              </div>
              <div className="bg-white rounded p-4 border border-blue-200">
                <div className="text-sm font-medium text-blue-900">TA-Aware Reliability</div>
                <div className="text-blue-700">JCO (84%) &gt; Nature (78%)</div>
                <div className="text-xs text-blue-600">✅ Recognizes domain expertise</div>
              </div>
            </div>
          </div>

          {/* Five Dimensions */}
          <div>
            <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
              <Target className="h-5 w-5 mr-2" />
              Five-Dimensional Assessment
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                {
                  name: 'Authority',
                  icon: <Award className="h-5 w-5" />,
                  description: 'TA-specific citation influence and recognition',
                  example: 'JCO gets 40% boost in oncology'
                },
                {
                  name: 'Relevance', 
                  icon: <Target className="h-5 w-5" />,
                  description: 'Semantic alignment to therapeutic area',
                  example: 'Specialization vs broad coverage'
                },
                {
                  name: 'Freshness',
                  icon: <Clock className="h-5 w-5" />,
                  description: 'Recent publication activity in TA',
                  example: 'Latest research in the field'
                },
                {
                  name: 'Guideline',
                  icon: <BookOpen className="h-5 w-5" />,
                  description: 'Presence in clinical guidelines',
                  example: 'NCCN, ASCO, FDA citations'
                },
                {
                  name: 'Rigor',
                  icon: <Shield className="h-5 w-5" />,
                  description: 'Editorial integrity and standards',
                  example: 'Peer review quality'
                }
              ].map((dimension, index) => (
                <div key={index} className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-2">
                    <div className="text-blue-600">{dimension.icon}</div>
                    <h4 className="font-semibold text-gray-900">{dimension.name}</h4>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{dimension.description}</p>
                  <p className="text-xs text-blue-600 font-medium">{dimension.example}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Use Cases */}
          <div>
            <h3 className="text-xl font-bold text-gray-900 mb-4">Use Case Optimization</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h4 className="font-bold text-green-900 mb-2">Clinical Use Case</h4>
                <p className="text-sm text-green-800 mb-3">For regulatory decisions and clinical practice</p>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-green-700">Authority:</span>
                    <span className="font-medium">45%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-green-700">Guideline:</span>
                    <span className="font-medium">25%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-green-700">Relevance:</span>
                    <span className="font-medium">20%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-green-700">Rigor:</span>
                    <span className="font-medium">5%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-green-700">Freshness:</span>
                    <span className="font-medium">5%</span>
                  </div>
                </div>
              </div>
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <h4 className="font-bold text-purple-900 mb-2">Exploratory Use Case</h4>
                <p className="text-sm text-purple-800 mb-3">For research discovery and innovation</p>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-purple-700">Relevance:</span>
                    <span className="font-medium">40%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-purple-700">Freshness:</span>
                    <span className="font-medium">25%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-purple-700">Authority:</span>
                    <span className="font-medium">20%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-purple-700">Rigor:</span>
                    <span className="font-medium">10%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-purple-700">Guideline:</span>
                    <span className="font-medium">5%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Color System */}
          <div>
            <h3 className="text-xl font-bold text-gray-900 mb-4">Reliability Bands</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { name: 'High', range: '80-100%', color: 'bg-blue-700', description: 'Highest confidence', icon: <Award className="h-4 w-4" /> },
                { name: 'Moderate', range: '60-79%', color: 'bg-sky-500', description: 'Good confidence', icon: <Target className="h-4 w-4" /> },
                { name: 'Exploratory', range: '40-59%', color: 'bg-orange-400', description: 'Moderate confidence', icon: <BookOpen className="h-4 w-4" /> },
                { name: 'Low', range: '0-39%', color: 'bg-gray-400', description: 'Lower confidence', icon: <Clock className="h-4 w-4" /> }
              ].map((band, index) => (
                <div key={index} className="text-center">
                  <div className={`${band.color} text-white rounded-lg py-3 px-2 mb-2`}>
                    <div className="flex items-center justify-center mb-1">{band.icon}</div>
                    <div className="font-bold">{band.name}</div>
                    <div className="text-xs">{band.range}</div>
                  </div>
                  <div className="text-xs text-gray-600">{band.description}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Real Examples */}
          <div className="bg-gray-50 rounded-lg p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">Real-World Examples</h3>
            <div className="space-y-3">
              {[
                { journal: 'JCO', ta: 'Oncology', useCase: 'Clinical', score: '84%', band: 'High', reason: 'Specialized authority + clinical guidelines', color: 'bg-blue-700' },
                { journal: 'Nature', ta: 'Oncology', useCase: 'Clinical', score: '78%', band: 'Moderate', reason: 'High rigor but broad scope', color: 'bg-sky-500' },
                { journal: 'Circulation', ta: 'Cardiovascular', useCase: 'Clinical', score: '85%', band: 'High', reason: 'Domain leader with guidelines', color: 'bg-blue-700' },
                { journal: 'PLOS ONE', ta: 'Any', useCase: 'Exploratory', score: '52%', band: 'Exploratory', reason: 'Open access + good freshness', color: 'bg-orange-400' }
              ].map((example, index) => (
                <div key={index} className="flex items-center justify-between bg-white rounded p-3 text-sm">
                  <div className="flex items-center space-x-4">
                    <span className="font-medium">{example.journal}</span>
                    <span className="text-gray-500">in {example.ta}</span>
                    <span className="text-gray-500">({example.useCase})</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="font-bold text-blue-600">Reliability Score: {example.score}</span>
                    <span className={`px-2 py-1 rounded text-xs text-white ${example.color}`}>
                      {example.band}
                    </span>
                    <span className="text-xs text-gray-500 max-w-xs">{example.reason}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
            <p className="text-blue-800 text-sm">
              This represents a shift from simple impact factors towards a sophisticated, 
              context-aware reliability assessment that aims to serve MSLs better.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ScoringExplanationModal;
