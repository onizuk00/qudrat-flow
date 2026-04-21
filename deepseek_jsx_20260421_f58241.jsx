import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { getTest, submitTest } from '../api/client';
import Timer from '../components/Timer';
import QuestionNavigator from '../components/QuestionNavigator';

const TestPage = () => {
  const { testId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const isRetest = location.pathname.includes('/retest/');
  const [test, setTest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [flaggedQuestions, setFlaggedQuestions] = useState(new Set());
  const [timeLimit, setTimeLimit] = useState(null);
  const [showTimeInput, setShowTimeInput] = useState(true);
  const [testStarted, setTestStarted] = useState(false);
  const [startTime, setStartTime] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    const loadTest = async () => {
      try {
        const testData = await getTest(testId);
        setTest(testData);
        const initialAnswers = {};
        testData.questions.forEach((_, idx) => { initialAnswers[idx] = undefined; });
        setAnswers(initialAnswers);
        setLoading(false);
      } catch (error) { navigate('/'); }
    };
    loadTest();
  }, [testId, navigate]);

  const handleStartTest = () => {
    if (timeLimit && timeLimit > 0) {
      setShowTimeInput(false);
      setTestStarted(true);
      setStartTime(Date.now());
    }
  };

  const handleTimeEnd = useCallback(async () => { if (testStarted && !result) await handleSubmit(); }, [testStarted, result]);

  const handleAnswer = (questionIdx, optionIndex) => setAnswers(prev => ({ ...prev, [questionIdx]: optionIndex }));
  const toggleFlag = (questionIdx) => setFlaggedQuestions(prev => { const newSet = new Set(prev); newSet.has(questionIdx) ? newSet.delete(questionIdx) : newSet.add(questionIdx); return newSet; });

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    const timeSpentSeconds = Math.floor((Date.now() - startTime) / 1000);
    const answersMap = {};
    test.questions.forEach((question, idx) => { if (answers[idx] !== undefined) answersMap[question.id] = answers[idx]; });
    try {
      const resultData = await submitTest(parseInt(testId), timeSpentSeconds, timeLimit * 60, answersMap);
      setResult(resultData);
    } catch (error) { console.error(error); } finally { setSubmitting(false); }
  };

  const handleFinish = () => navigate('/');

  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="text-xl">جاري تحميل الاختبار...</div></div>;
  if (result) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-8 text-center">
        <div className="text-6xl mb-4">📊</div>
        <h2 className="text-2xl font-bold mb-2">نتيجة الاختبار</h2>
        <div className="text-5xl font-bold text-blue-600 my-4">{result.percentage}%</div>
        <div className="text-gray-600 mb-6">{result.correct_count} من {result.total_questions} إجابات صحيحة</div>
        <button onClick={handleFinish} className="w-full bg-blue-600 text-white py-3 rounded-lg font-bold hover:bg-blue-700">العودة إلى الرئيسية</button>
      </div>
    </div>
  );
  if (showTimeInput) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-8 text-center">
        <h2 className="text-2xl font-bold mb-4">{test?.title}</h2>
        <p className="text-gray-600 mb-6">حدد الوقت المخصص للاختبار</p>
        <input type="number" value={timeLimit || ''} onChange={(e) => setTimeLimit(parseInt(e.target.value) || 0)} placeholder="الوقت بالدقائق" className="w-full p-3 border rounded-lg mb-4 text-center text-lg" min="1" />
        <button onClick={handleStartTest} disabled={!timeLimit || timeLimit <= 0} className="w-full bg-green-600 text-white py-3 rounded-lg font-bold hover:bg-green-700 disabled:opacity-50">بدء الاختبار</button>
      </div>
    </div>
  );
  const currentQuestion = test.questions[currentQuestionIndex];
  const hasReadingPassage = test.reading_passage && test.reading_passage.trim().length > 0;
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm sticky top-0 z-10 p-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Timer initialSeconds={timeLimit * 60} onTimeEnd={handleTimeEnd} isRunning={testStarted && !result} />
          <h1 className="text-lg font-bold text-right flex-1 mx-4">{test?.title}</h1>
          <button onClick={handleSubmit} disabled={submitting} className="bg-blue-600 text-white px-6 py-2 rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50">{submitting ? 'جاري التصحيح...' : 'إنهاء الاختبار'}</button>
        </div>
      </div>
      <div className="max-w-7xl mx-auto p-4">
        <div className="flex flex-col lg:flex-row gap-6">
          <div className="lg:w-1/4">
            <QuestionNavigator totalQuestions={test.questions.length} answers={answers} flaggedQuestions={flaggedQuestions} currentIndex={currentQuestionIndex} onNavigate={setCurrentQuestionIndex} />
            <div className="mt-4 bg-white rounded-xl shadow-sm p-4">
              <button onClick={() => toggleFlag(currentQuestionIndex)} className={`w-full py-2 rounded-lg font-medium transition ${flaggedQuestions.has(currentQuestionIndex) ? 'bg-yellow-500 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}>{flaggedQuestions.has(currentQuestionIndex) ? 'إزالة العلامة' : 'تحديد للمراجعة'}</button>
            </div>
          </div>
          <div className="lg:w-3/4">
            <div className="bg-white rounded-xl shadow-sm p-6">
              {hasReadingPassage && currentQuestionIndex === 0 && (
                <div className="mb-6 p-4 bg-blue-50 rounded-lg border-r-4 border-blue-500">
                  <h3 className="font-bold mb-2">نص الاستيعاب:</h3>
                  <p className="text-gray-700 leading-relaxed">{test.reading_passage}</p>
                </div>
              )}
              <div className="mb-6">
                <div className="flex justify-between items-center mb-4"><span className="text-sm text-gray-500">السؤال {currentQuestionIndex + 1} من {test.questions.length}</span></div>
                <p className="text-lg font-medium mb-6 leading-relaxed">{currentQuestion.text}</p>
                <div className="space-y-3">
                  {currentQuestion.options.map((option, optIdx) => {
                    const optionLetter = ['أ', 'ب', 'ج', 'د'][optIdx] || String.fromCharCode(65 + optIdx);
                    return (
                      <label key={optIdx} className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition ${answers[currentQuestionIndex] === optIdx ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'}`}>
                        <input type="radio" name={`question-${currentQuestionIndex}`} value={optIdx} checked={answers[currentQuestionIndex] === optIdx} onChange={() => handleAnswer(currentQuestionIndex, optIdx)} className="w-5 h-5" />
                        <span className="font-bold w-8">{optionLetter}.</span><span className="flex-1">{option}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
              <div className="flex justify-between mt-8">
                <button onClick={() => setCurrentQuestionIndex(prev => Math.max(0, prev - 1))} disabled={currentQuestionIndex === 0} className="px-6 py-2 bg-gray-200 rounded-lg font-medium disabled:opacity-50">السابق</button>
                <button onClick={() => setCurrentQuestionIndex(prev => Math.min(test.questions.length - 1, prev + 1))} disabled={currentQuestionIndex === test.questions.length - 1} className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium disabled:opacity-50">التالي</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TestPage;