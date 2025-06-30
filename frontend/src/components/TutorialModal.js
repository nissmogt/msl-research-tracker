import React, { useState, useEffect } from 'react';

const steps = [
  {
    title: 'Welcome',
    content: `Welcome to the MSL Research Tracker!\n\nThis quick tutorial will show you how to get the most out of the app.`,
  },
  {
    title: 'Search Bar',
    content: `Enter a therapeutic area (e.g., Oncology, Immunology) in the search bar to find research articles.`,
  },
  {
    title: 'Search Modes',
    content: `Toggle between "Local Database" and "PubMed Search" to find saved or new articles.`,
  },
  {
    title: 'Article Details',
    content: `Click an article to view details, open it in PubMed, or generate AI insights.`,
  },
  {
    title: 'Save & Insights',
    content: `Save articles for later, and click "Generate Insights" for AI-powered summaries.\n\nNo need to save first—insights work instantly!`,
  },
  {
    title: 'Time Range',
    content: `Use the time range dropdown to filter articles by publication date.`,
  },
  {
    title: 'Access Tutorial Anytime',
    content: `You can always revisit this tutorial by clicking the "?" button in the bottom right corner.`,
  },
];

export default function TutorialModal({ open, onClose }) {
  const [step, setStep] = useState(0);

  // Reset step to 0 whenever modal is opened
  useEffect(() => {
    if (open) setStep(0);
  }, [open]);

  // Disable background scroll when modal is open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  if (!open) return null;

  const handleNext = () => setStep((s) => Math.min(s + 1, steps.length - 1));
  const handleBack = () => setStep((s) => Math.max(s - 1, 0));
  const handleExit = () => {
    setStep(0);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 relative animate-fade-in">
        <h2 className="text-xl font-bold mb-2 text-primary-700">{steps[step].title}</h2>
        <div className="mb-6 whitespace-pre-line text-gray-700">{steps[step].content}</div>
        <div className="flex justify-between items-center">
          <button
            onClick={handleBack}
            disabled={step === 0}
            className="px-4 py-2 rounded bg-gray-200 text-gray-700 disabled:opacity-50"
          >
            Back
          </button>
          <span className="text-xs text-gray-500">Step {step + 1} of {steps.length}</span>
          {step === steps.length - 1 ? (
            <button
              onClick={handleExit}
              className="px-4 py-2 rounded bg-primary-600 text-white hover:bg-primary-700"
            >
              Finish
            </button>
          ) : (
            <button
              onClick={handleNext}
              className="px-4 py-2 rounded bg-primary-600 text-white hover:bg-primary-700"
            >
              Continue
            </button>
          )}
        </div>
        <button
          onClick={handleExit}
          className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 text-lg"
          title="Exit tutorial"
        >
          ×
        </button>
      </div>
    </div>
  );
} 