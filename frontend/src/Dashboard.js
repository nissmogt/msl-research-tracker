import React, { useState, useEffect } from 'react';
import axios from 'axios';
import TutorialModal from './components/TutorialModal';
// ...existing imports...

function Dashboard() {
  // ...existing state...
  const [showTutorial, setShowTutorial] = useState(() => {
    return localStorage.getItem('msl_tutorial_complete') !== 'true';
  });

  const handleTutorialClose = () => {
    setShowTutorial(false);
    localStorage.setItem('msl_tutorial_complete', 'true');
  };

  // ...existing code...

  return (
    <div className="h-screen flex bg-gray-50">
      {/* Tutorial Modal */}
      <TutorialModal open={showTutorial} onClose={handleTutorialClose} />
      {/* '?' Button */}
      <button
        onClick={() => setShowTutorial(true)}
        className="fixed top-4 right-4 z-50 bg-primary-600 text-white rounded-full w-10 h-10 flex items-center justify-center shadow-lg hover:bg-primary-700 focus:outline-none"
        title="Show tutorial"
        style={{ fontSize: 24 }}
      >
        ?
      </button>
      {/* Main Content */}
      {/* ...existing content... */}
    </div>
  );
}

export default Dashboard; 