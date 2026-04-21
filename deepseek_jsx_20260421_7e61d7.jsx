import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getMistakes, retestMistakes } from '../api/client';

const MistakesPage = () => {
  const { testId } = useParams();
  const navigate = useNavigate();
  const [mistakes, setMistakes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testTitle, setTestTitle] = useState('');

  useEffect(() => { loadMistakes(); }, [testId]);

  const loadMistakes = async () => {
    try {
      const data = await getMistakes(testId ? parseInt(testId) : null);
      setMistakes(data);
      if (data.length > 0 && testId) setTestTitle(data[0].test_title);
    } catch (error) { console.error(error); } finally { setLoading(false); }
  };

  const handleRetest = async () => {
    try {
      await retestMistakes(parseInt(testId));
      navigate(`/retest/${testId}`);
    } catch (error) { alert('لا توجد أخطاء مسجلة لهذا الاختبار'); }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="text-xl">جاري التحميل...</div></div>;
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <button onClick={() => navigate('/')} className="text-blue-600 hover:text-blue-800">← العودة للرئيسية</button>
          <h1 className="text-2xl font-bold text-right">سجل الأخطاء</h1>
        </div>
        {testTitle && (
          <div className="bg-white rounded-xl shadow-md p-4 mb-6 text-center">
            <h2 className="text-xl font-bold">{testTitle}</h2>
            <button onClick={handleRetest} className="mt-3 bg-purple-600 text-white px-6 py-2 rounded-lg font-bold hover:bg-purple-700">مراجعة الأخطاء فقط</button>
          </div>
        )}
        {mistakes.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md p-8 text-center"><div className="text-6xl mb-4">🎉</div><p className="text-gray-600">لا توجد أخطاء! أداؤك ممتاز</p></div>
        ) : (
          <div className="space-y-4">
            {mistakes.map((mistake, idx) => {
              const options = JSON.parse(mistake.options_json);
              const correctOption = options[mistake.correct_answer_index];
              const selectedOption = options[mistake.selected_answer_index];
              const optionLetter = ['أ', 'ب', 'ج', 'د'][mistake.correct_answer_index] || '';
              return (
                <div key={mistake.id} className="bg-white rounded-xl shadow-md p-5 border-r-4 border-red-500">
                  <div className="flex justify-between items-start mb-3"><span className="text-sm text-gray-400">{new Date(mistake.start_time).toLocaleDateString('ar-SA')}</span><span className="text-sm font-bold text-gray-500">الخطأ #{idx + 1}</span></div>
                  <p className="font-medium mb-3">{mistake.question_text}</p>
                  <div className="bg-red-50 p-3 rounded-lg mb-2"><p className="text-sm text-red-700">❌ إجابتك: {selectedOption}</p></div>
                  <div className="bg-green-50 p-3 rounded-lg"><p className="text-sm text-green-700">✅ الإجابة الصحيحة: {optionLetter}. {correctOption}</p></div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default MistakesPage;