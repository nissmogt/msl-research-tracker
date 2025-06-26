import React from 'react';
import axios from 'axios';
import Dashboard from './components/Dashboard';

// Configure axios defaults - use Railway backend in production
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://msl-research-tracker-production.up.railway.app';
axios.defaults.baseURL = API_BASE_URL;

function App() {
  return (
    <div className="App">
      <Dashboard />
    </div>
  );
}

export default App; 