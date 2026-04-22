import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';

function Home() {
  return <div className="p-8 text-center"><h1 className="text-2xl font-bold">مرحباً بك في قدرات فلو</h1><p>التطبيق يعمل بنجاح 🎉</p></div>;
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
    </Routes>
  );
}

export default App;
