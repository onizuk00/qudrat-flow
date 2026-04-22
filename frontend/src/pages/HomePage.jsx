import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getTests, scrapeTest, getHistory } from '../api/client';
import { useTheme } from '../context/ThemeContext';

const HomePage = () => {
  const navigate = useNavigate();
  const { darkMode, setDarkMode } = useTheme();
  const [tests, setTests] = useState([]);
  const [history, setHistory] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [formUrl, setFormUrl] = useState('');
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeError, setScrapeError] = useState('');
  const [scrapeProgress, setScrapeProgress] = useState(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [testsData, historyData] = await Promise.all([getTests(), getHistory()]);
      setTests(testsData);
      setHistory(historyData);
    } catch (error) { console.error(error); }
  };

  const handleAddTest = async () => {
    if (!formUrl.trim()) { setScrapeError('الرجاء إدخال رابط Google Form'); return; }
    setIsScraping(true);
    setScrapeError('');
    setScrapeProgress('جاري تحليل النموذج... (قد يستغرق 10-20 ثانية)');
    try {
      const result = await scrapeTest(formUrl);
      await loadData();
      setShowAddModal(false);
      setFormUrl('');
      navigate(`/test/${result.test_id}`);
    } catch (error) {
      setScrapeError(error.response?.data?.detail || 'فشل في استخراج البيانات. تأكد من الرابط');
    } finally { setIsScraping(false); setScrapeProgress(null); }
  };

  const handleStartTest = (testId) => navigate(`/test/${testId}`);
  const handleViewMistakes = (testId) => navigate(`/mistakes/${testId}`);
  const handleRetestMistakes = (testId) => navigate(`/retest/${testId}`);

  return (
    <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`}>
      <div className="max-w-6xl mx-auto p-6">
        {/* Header with Dark Mode Toggle */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-teal-500 bg-clip-text text-transparent">قدرات فلو</h1>
          <div className="flex gap-3">
            <button
              onClick={() => setDarkMode(!darkMode)}
              className={`p-2 rounded-full ${darkMode ? 'bg-yellow-400 text-gray-900' : 'bg-gray-800 text-yellow-400'}`}
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-2 rounded-xl font-bold hover:shadow-lg transition"
            >
              + إضافة اختبار جديد
            </button>
          </div>
        </div>

        {/* Tests Library */}
        <div className={`rounded-2xl shadow-lg p-6 mb-8 transition ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <h2 className="text-xl font-bold mb-4 text-right">📚 مكتبة الاختبارات</h2>
          {tests.length === 0 ? (
            <p className="text-center py-8 opacity-70">لا توجد اختبارات. أضف اختباراً جديداً للبدء</p>
          ) : (
            <div className="grid gap-4">
              {tests.map((test) => (
                <div key={test.id} className={`border rounded-xl p-4 transition hover:shadow-md ${darkMode ? 'border-gray-700 hover:bg-gray-700' : 'border-gray-200 hover:bg-gray-50'}`}>
                  <div className="flex justify-between items-center flex-wrap gap-4">
                    <div className="flex gap-2">
                      <button onClick={() => handleStartTest(test.id)} className="bg-green-600 hover:bg-green-700 text-white px-5 py-2 rounded-lg font-medium transition">بدء الاختبار</button>
                      <button onClick={() => handleViewMistakes(test.id)} className="bg-orange-500 hover:bg-orange-600 text-white px-5 py-2 rounded-lg font-medium transition">الأخطاء</button>
                      {test.last_score !== null && <button onClick={() => handleRetestMistakes(test.id)} className="bg-purple-600 hover:bg-purple-700 text-white px-5 py-2 rounded-lg font-medium transition">مراجعة الأخطاء</button>}
                    </div>
                    <div className="text-right">
                      <h3 className="font-bold text-lg">{test.title}</h3>
                      {test.last_score !== null && <div className="text-sm opacity-75">آخر محاولة: {test.last_score}% ({test.last_correct}/{test.last_total})</div>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* History Table */}
        {history.length > 0 && (
          <div className={`rounded-2xl shadow-lg p-6 transition ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <h2 className="text-xl font-bold mb-4 text-right">📜 سجل الاختبارات</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-right">
                <thead className={`${darkMode ? 'bg-gray-700' : 'bg-gray-100'}`}>
                  <tr><th className="p-3 rounded-r-lg">الاختبار</th><th className="p-3">التاريخ</th><th className="p-3">الدرجة</th><th className="p-3 rounded-l-lg">النتيجة</th></tr>
                </thead>
                <tbody>
                  {history.map((session) => (
                    <tr key={session.id} className={`border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                      <td className="p-3 font-medium">{session.test_title}</td>
                      <td className="p-3 opacity-75">{new Date(session.start_time).toLocaleString('ar-SA')}</td>
                      <td className="p-3">{session.score}%</td>
                      <td className="p-3"><span className={`px-3 py-1 rounded-full text-sm ${session.score >= 70 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : session.score >= 50 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}`}>{session.correct_count}/{session.total_questions}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Add Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
            <div className={`rounded-2xl max-w-md w-full p-6 shadow-xl transition ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
              <h3 className="text-xl font-bold mb-4 text-right">إضافة اختبار جديد</h3>
              <input
                type="text"
                value={formUrl}
                onChange={(e) => setFormUrl(e.target.value)}
                placeholder="https://docs.google.com/forms/..."
                className={`w-full p-3 border rounded-xl mb-4 text-right focus:outline-none focus:ring-2 focus:ring-blue-500 ${darkMode ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300'}`}
                dir="ltr"
              />
              {scrapeProgress && <p className="text-blue-500 text-sm mb-2 text-center animate-pulse">{scrapeProgress}</p>}
              {scrapeError && <p className="text-red-500 text-sm mb-4 text-center">{scrapeError}</p>}
              <div className="flex gap-3">
                <button onClick={handleAddTest} disabled={isScraping} className="flex-1 bg-blue-600 text-white py-2 rounded-xl font-bold hover:bg-blue-700 disabled:opacity-50 transition">استخراج وبدء الاختبار</button>
                <button onClick={() => setShowAddModal(false)} className="flex-1 bg-gray-400 text-white py-2 rounded-xl font-bold hover:bg-gray-500 transition">إلغاء</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default HomePage;
