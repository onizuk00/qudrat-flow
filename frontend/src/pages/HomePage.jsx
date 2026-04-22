import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getTests, scrapeTest, getHistory } from '../api/client';

const HomePage = () => {
  const navigate = useNavigate();
  const [tests, setTests] = useState([]);
  const [history, setHistory] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [formUrl, setFormUrl] = useState('');
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeError, setScrapeError] = useState('');

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
    try {
      const result = await scrapeTest(formUrl);
      await loadData();
      setShowAddModal(false);
      setFormUrl('');
      navigate(`/test/${result.test_id}`, { state: { timeLimit: null } });
    } catch (error) {
      setScrapeError(error.response?.data?.detail || 'فشل في استخراج البيانات');
    } finally { setIsScraping(false); }
  };

  const handleStartTest = (testId) => navigate(`/test/${testId}`, { state: { timeLimit: null } });
  const handleViewMistakes = (testId) => navigate(`/mistakes/${testId}`);
  const handleRetestMistakes = (testId) => navigate(`/retest/${testId}`);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-blue-700">قدرات فلو</h1>
          <button onClick={() => setShowAddModal(true)} className="bg-blue-600 text-white px-6 py-2 rounded-lg font-bold hover:bg-blue-700 flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
            إضافة اختبار جديد
          </button>
        </div>
        <div className="bg-white rounded-xl shadow-md p-6 mb-8">
          <h2 className="text-xl font-bold mb-4 text-right">مكتبة الاختبارات</h2>
          {tests.length === 0 ? <p className="text-gray-500 text-center py-8">لا توجد اختبارات. أضف اختباراً جديداً للبدء</p> : (
            <div className="grid gap-4">
              {tests.map((test) => (
                <div key={test.id} className="border rounded-lg p-4 hover:shadow-lg transition">
                  <div className="flex justify-between items-center flex-wrap gap-4">
                    <div className="flex gap-2">
                      <button onClick={() => handleStartTest(test.id)} className="bg-green-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700">بدء الاختبار</button>
                      <button onClick={() => handleViewMistakes(test.id)} className="bg-orange-500 text-white px-4 py-2 rounded-lg font-medium hover:bg-orange-600">عرض الأخطاء</button>
                      {test.last_score !== null && <button onClick={() => handleRetestMistakes(test.id)} className="bg-purple-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-purple-700">مراجعة الأخطاء</button>}
                    </div>
                    <div className="text-right">
                      <h3 className="font-bold text-lg">{test.title}</h3>
                      {test.last_score !== null && <div className="text-sm text-gray-600 mt-1">آخر محاولة: {test.last_score}% ({test.last_correct}/{test.last_total})</div>}
                      {test.last_taken && <div className="text-xs text-gray-400">{new Date(test.last_taken).toLocaleDateString('ar-SA')}</div>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        {history.length > 0 && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-xl font-bold mb-4 text-right">سجل الاختبارات</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-right">
                <thead className="bg-gray-100"><tr><th className="p-3 rounded-r-lg">الاختبار</th><th className="p-3">التاريخ</th><th className="p-3">الدرجة</th><th className="p-3 rounded-l-lg">النتيجة</th></tr></thead>
                <tbody>
                  {history.map((session) => (
                    <tr key={session.id} className="border-b hover:bg-gray-50">
                      <td className="p-3 font-medium">{session.test_title}</td>
                      <td className="p-3 text-gray-600">{new Date(session.start_time).toLocaleString('ar-SA')}</td>
                      <td className="p-3">{session.score}%</td>
                      <td className="p-3"><span className={`px-2 py-1 rounded-full text-sm ${session.score >= 70 ? 'bg-green-100 text-green-700' : session.score >= 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>{session.correct_count}/{session.total_questions} صحيح</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {showAddModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl max-w-md w-full p-6">
              <h3 className="text-xl font-bold mb-4 text-right">إضافة اختبار جديد</h3>
              <input type="text" value={formUrl} onChange={(e) => setFormUrl(e.target.value)} placeholder="https://docs.google.com/forms/..." className="w-full p-3 border rounded-lg mb-4 text-right" dir="ltr" />
              {scrapeError && <p className="text-red-600 text-sm mb-4">{scrapeError}</p>}
              <div className="flex gap-3">
                <button onClick={handleAddTest} disabled={isScraping} className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50">{isScraping ? 'جاري الاستخراج...' : 'استخراج وبدء الاختبار'}</button>
                <button onClick={() => setShowAddModal(false)} className="flex-1 bg-gray-300 text-gray-700 py-2 rounded-lg font-bold hover:bg-gray-400">إلغاء</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default HomePage;
