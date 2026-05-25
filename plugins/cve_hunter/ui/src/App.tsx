import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import CVEHunterPanel from './components/CVEHunterPanel';
import { AuthProvider, ProtectedRoute, LoginPage } from '@auth';

// Wrapper to handle login success redirect logic
const LoginWrapper = () => {
  const handleLoginSuccess = () => {
    // The AuthProvider/LoginPage usually handles redirect via query param,
    // but we can enforce a default here if needed.
    const params = new URLSearchParams(window.location.search);
    const redirect = params.get('redirect') || '/cve_hunter/';
    window.location.href = redirect;
  };

  return <LoginPage onSuccess={handleLoginSuccess} />;
};

const App = () => {
  return (
    <AuthProvider>
      <Router basename="/cve_hunter">
        <Routes>
          <Route path="/login" element={<LoginWrapper />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <div className="app-container">
                  <CVEHunterPanel />
                </div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;
