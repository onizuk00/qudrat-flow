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
  const [scrapeStep, setScrapeStep] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [testsData, historyData] = await Promise.all([getTests(), getHistory()]);
      setTests(testsData);
      setHistory(historyData);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const handleAddTest = async () => {
    if (!formUrl.trim()) {
      setScrapeError('الرجاء إدخال رابط Google Form');
      return;
    }
    setIsScraping(true);
    setScrapeError('');
    setScrapeStep('جاري تحليل النموذج...');
    
    try {
      const result = await scrapeTest(formUrl);
      await loadData();
      setShowAddModal(false);
      setFormUrl('');
      setScrapeStep('');
      navigate(`/test/${result.test_id}`);
    } catch (error) {
      setScrapeError(error.response?.data?.detail || 'فشل في استخراج البيانات. تأكد من الرابط');
    } finally {
      setIsScraping(false);
      setScrapeStep('');
    }
  };

  const handleStartTest = (testId) => navigate(`/test/${testId}`);
  const handleViewMistakes = (testId) => navigate(`/mistakes/${testId}`);
  const handleRetestMistakes = (testId) => navigate(`/retest/${testId}`);

  // Helper to get score color class
  const getScoreColor = (score) => {
    if (score >= 70) return 'text-green-600 dark:text-green-400';
    if (score >= 50) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div className="min-h-screen transition-all duration-500 fade-in">
      {/* Hero Section مع خلفية متدرجة */}
      <div className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-white to-teal-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
        <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
        <div className="max-w-7xl mx-auto px-6 py-8 relative z-10">
          {/* Header */}
          <div className="flex flex-wrap justify-between items-center gap-4 mb-12">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-teal-500 rounded-2xl flex items-center justify-center shadow-lg">
                <i className="fas fa-brain text-white text-2xl"></i>
              </div>
              <h1 className="text-4xl font-black gradient-text">قدرات فلو</h1>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="w-12 h-12 rounded-full bg-white dark:bg-gray-800 shadow-md flex items-center justify-center text-xl transition-all duration-300 hover:scale-110"
              >
                {darkMode ? '☀️' : '🌙'}
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                className="btn-primary flex items-center gap-2"
              >
                <i className="fas fa-plus-circle"></i>
                <span>إضافة اختبار جديد</span>
              </button>
            </div>
          </div>

          {/* Welcome Card */}
          <div className="glass-card p-8 mb-12 text-center fade-in">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-teal-500 rounded-2xl shadow-lg mb-4">
              <i className="fas fa-chalkboard-user text-white text-3xl"></i>
            </div>
            <h2 className="text-3xl font-bold mb-2 gradient-text">مرحباً بك في قدرات فلو</h2>
            <p className="text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
              منصة متكاملة لاختبارات القدرات اللفظية. أضف اختبارات Google Forms الخاصة بك،
              واخضع لها في بيئة احترافية مع مؤقت، وتتبع الأخطاء، وإعادة المحاولة.
            </p>
          </div>

          {/* Tests Library */}
          <div className="glass-card p-8 mb-12 transition-all duration-300">
            <div className="flex justify-between items-center mb-6">
              <i className="fas fa-book-open text-2xl text-blue-600 dark:text-blue-400"></i>
              <h2 className="text-2xl font-bold text-right flex-1 mr-3">مكتبة الاختبارات</h2>
            </div>
            {tests.length === 0 ? (
              <div className="text-center py-12">
                <i className="fas fa-folder-open text-6xl text-gray-400 mb-4"></i>
                <p className="text-gray-500 dark:text-gray-400">لا توجد اختبارات بعد. أضف اختبارك الأول الآن!</p>
              </div>
            ) : (
              <div className="grid gap-5">
                {tests.map((test, idx) => (
                  <div
                    key={test.id}
                    className="group bg-white dark:bg-gray-800 rounded-xl p-5 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 border border-gray-100 dark:border-gray-700 fade-in"
                    style={{ animationDelay: `${idx * 0.05}s` }}
                  >
                    <div className="flex flex-wrap justify-between items-center gap-4">
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleStartTest(test.id)}
                          className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white px-5 py-2.5 rounded-lg font-medium transition-all duration-300 flex items-center gap-2 shadow-md hover:shadow-lg"
                        >
                          <i className="fas fa-play"></i>
                          <span>بدء الاختبار</span>
                        </button>
                        <button
                          onClick={() => handleViewMistakes(test.id)}
                          className="bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white px-5 py-2.5 rounded-lg font-medium transition-all duration-300 flex items-center gap-2 shadow-md"
                        >
                          <i className="fas fa-chart-line"></i>
                          <span>الأخطاء</span>
                        </button>
                        {test.last_score !== null && (
                          <button
                            onClick={() => handleRetestMistakes(test.id)}
                            className="bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white px-5 py-2.5 rounded-lg font-medium transition-all duration-300 flex items-center gap-2 shadow-md"
                          >
                            <i className="fas fa-redo-alt"></i>
                            <span>مراجعة الأخطاء</span>
                          </button>
                        )}
                      </div>
                      <div className="text-right">
                        <h3 className="font-bold text-lg flex items-center gap-2">
                          <i className="fas fa-file-alt text-blue-500 text-sm"></i>
                          {test.title}
                        </h3>
                        {test.last_score !== null && (
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`text-xl font-bold ${getScoreColor(test.last_score)}`}>
                              {test.last_score}%
                            </span>
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                              ({test.last_correct}/{test.last_total})
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* History Table */}
          {history.length > 0 && (
            <div className="glass-card p-8 fade-in">
              <div className="flex items-center gap-3 mb-6">
                <i className="fas fa-history text-2xl text-teal-500"></i>
                <h2 className="text-2xl font-bold">سجل الاختبارات</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-right">
                  <thead className="bg-gray-100 dark:bg-gray-700 rounded-xl">
                    <tr>
                      <th className="p-3 rounded-tr-xl">الاختبار</th>
                      <th className="p-3">التاريخ</th>
                      <th className="p-3">الدرجة</th>
                      <th className="p-3 rounded-tl-xl">النتيجة</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((session) => (
                      <tr key={session.id} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition">
                        <td className="p-3 font-medium">{session.test_title}</td>
                        <td className="p-3 text-gray-500 dark:text-gray-400 text-sm">
                          {new Date(session.start_time).toLocaleDateString('ar-SA')}
                        </td>
                        <td className={`p-3 font-bold ${getScoreColor(session.score)}`}>
                          {session.score}%
                        </td>
                        <td className="p-3">
                          <span className={`px-3 py-1 rounded-full text-sm ${session.score >= 70 ? 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300' : session.score >= 50 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300' : 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300'}`}>
                            {session.correct_count}/{session.total_questions}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 fade-in">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-md w-full p-6 shadow-2xl transform transition-all duration-300 scale-100">
            <div className="flex justify-between items-center mb-4">
              <i className="fas fa-link text-2xl text-blue-500"></i>
              <h3 className="text-xl font-bold text-right flex-1 mr-3">إضافة اختبار جديد</h3>
              <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <i className="fas fa-times text-xl"></i>
              </button>
            </div>
            <input
              type="text"
              value={formUrl}
              onChange={(e) => setFormUrl(e.target.value)}
              placeholder="https://docs.google.com/forms/..."
              className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-xl mb-4 text-right focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white transition"
              dir="ltr"
            />
            {scrapeStep && (
              <div className="mb-4 text-center">
                <div className="inline-flex items-center gap-2 text-blue-600 dark:text-blue-400">
                  <i className="fas fa-spinner fa-pulse"></i>
                  <span>{scrapeStep}</span>
                </div>
              </div>
            )}
            {scrapeError && (
              <div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-xl text-center text-sm">
                <i className="fas fa-exclamation-triangle ml-2"></i>
                {scrapeError}
              </div>
            )}
            <div className="flex gap-3">
              <button
                onClick={handleAddTest}
                disabled={isScraping}
                className="flex-1 bg-gradient-to-r from-blue-600 to-blue-700 text-white py-3 rounded-xl font-bold hover:shadow-lg transition-all duration-300 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isScraping ? <i className="fas fa-spinner fa-pulse"></i> : <i className="fas fa-download"></i>}
                <span>{isScraping ? 'جاري الاستخراج...' : 'استخراج وبدء الاختبار'}</span>
              </button>
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-white py-3 rounded-xl font-bold hover:bg-gray-400 dark:hover:bg-gray-500 transition"
              >
                إلغاء
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HomePage;
