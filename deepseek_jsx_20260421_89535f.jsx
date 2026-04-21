import React from 'react';
import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import TestPage from './pages/TestPage';
import MistakesPage from './pages/MistakesPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/test/:testId" element={<TestPage />} />
      <Route path="/retest/:testId" element={<TestPage />} />
      <Route path="/mistakes/:testId?" element={<MistakesPage />} />
    </Routes>
  );
}

export default App;