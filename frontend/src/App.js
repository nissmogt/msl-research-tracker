import React from 'react';
import axios from 'axios';
import Dashboard from './components/Dashboard';

// Configure axios defaults - use local /api proxy to Railway backend
// This ensures all requests go through our secure Vercel proxy
axios.defaults.baseURL = '/api';

function App() {
  return (
    <div className="App">
      <Dashboard />
    </div>
  );
}

export default App; 