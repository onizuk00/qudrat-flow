import React from 'react';

const QuestionNavigator = ({ totalQuestions, answers, flaggedQuestions, currentIndex, onNavigate }) => {
  const getStatus = (index) => {
    if (flaggedQuestions.has(index)) return 'flagged';
    if (answers[index] !== undefined) return 'answered';
    return 'pending';
  };

  const getCircleClass = (status) => {
    switch (status) {
      case 'answered': return 'question-circle-answered';
      case 'flagged': return 'question-circle-flagged';
      default: return 'question-circle-pending';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm p-4">
      <h3 className="text-lg font-bold mb-4 text-right">أسئلة الاختبار</h3>
      <div className="grid grid-cols-5 gap-2">
        {Array.from({ length: totalQuestions }).map((_, idx) => {
          const status = getStatus(idx);
          return (
            <button
              key={idx}
              onClick={() => onNavigate(idx)}
              className={`question-circle ${getCircleClass(status)} ${currentIndex === idx ? 'ring-2 ring-blue-500 ring-offset-2' : ''}`}
            >
              {idx + 1}
            </button>
          );
        })}
      </div>
      <div className="mt-4 flex justify-around text-xs text-gray-600">
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-green-500"></div><span>تمت الإجابة</span></div>
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-yellow-500"></div><span>للرجوع إليه</span></div>
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-gray-300"></div><span>لم تجب</span></div>
      </div>
    </div>
  );
};

export default QuestionNavigator;
