import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AdminPanel from './components/AdminPanel';
import { AuthProvider, ProtectedRoute, LoginPage } from './index';

const LoginWrapper = () => {
  const handleLoginSuccess = () => {
    const params = new URLSearchParams(window.location.search);
    const redirect = params.get('redirect') || '/auth/';
    window.location.href = redirect;
  };

  return <LoginPage onSuccess={handleLoginSuccess} />;
};

const App = () => {
  return (
    <AuthProvider>
      <Router basename="/auth">
        <Routes>
          <Route path="/login" element={<LoginWrapper />} />
          <Route
            path="/"
            element={
              <ProtectedRoute requiredRole="admin">
                <AdminPanel />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;
