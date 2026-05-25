import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HoneypotPanel from './components/HoneypotPanel';
import { AuthProvider, LoginPage, ProtectedRoute } from '@auth';

// Wrapper for the shared LoginPage to handle successful login redirect
function LoginWrapper() {
  return (
    <LoginPage
      onSuccess={() => {
        // The redirects are handled by the AuthContext/LoginPage logic usually,
        // but if we need explicit redirect:
        const params = new URLSearchParams(window.location.search);
        const redirect = params.get('redirect') || '/';
        window.location.href = '/honeypot' + (redirect === '/' ? '' : redirect);
      }}
    />
  );
}

function App() {
  return (
    <BrowserRouter basename="/honeypot/">
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginWrapper />} />
          <Route
            path="*"
            element={
              <ProtectedRoute>
                <HoneypotPanel />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
