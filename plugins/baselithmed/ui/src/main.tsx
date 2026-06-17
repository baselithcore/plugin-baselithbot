import React from 'react';
import { createRoot } from 'react-dom/client';
import { AuthProvider } from '@auth';
import { ProtectedRoute } from '@auth/login';
import App from './App';
import './index.css';

const root = document.getElementById('root');
if (root) {
  createRoot(root).render(
    <React.StrictMode>
      <AuthProvider>
        <ProtectedRoute>
          <App />
        </ProtectedRoute>
      </AuthProvider>
    </React.StrictMode>
  );
}
