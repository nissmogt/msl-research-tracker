import React from 'react';
import axios from 'axios';
import Dashboard from './components/Dashboard';

// Configure axios defaults
axios.defaults.baseURL = 'http://localhost:8000';

function App() {
  return (
    <div className="App">
      <Dashboard />
    </div>
  );
}

export default App; 