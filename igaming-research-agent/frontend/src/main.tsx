import React from 'react';
import ReactDOM from 'react-dom/client';

import App from './App';
import './index.css';

// TODO: Add top-level error boundary and app-level providers.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
