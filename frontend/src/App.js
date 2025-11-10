import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';

import RegisterPage from './pages/RegisterPage'; 

const HomePage = () => <h1>Home Page</h1>;

const LoginPage = () => <h1>Login Page</h1>;

function App() {
  return (
    <div>
      <nav>
        <Link to="/">Home</Link> | {" "}
        <Link to="/register">Register</Link> | {" "}
        <Link to="/login">Login</Link>
      </nav>
      <hr />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/register" element={<RegisterPage />} /> 
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    </div>
  );
}

export default App;