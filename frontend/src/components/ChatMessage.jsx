export default function ChatMessage({ message, isUser }) {
  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 text-white text-sm">🤖</div>
      )}
      
      <div className={`max-w-[70%] rounded-lg px-4 py-3 ${
        isUser
          ? 'bg-blue-600 text-white'
          : 'bg-gray-100 text-gray-900'
      }`}>
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          {message}
        </p>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center flex-shrink-0 text-gray-700 text-sm">👤</div>
      )}
    </div>
  );
}
