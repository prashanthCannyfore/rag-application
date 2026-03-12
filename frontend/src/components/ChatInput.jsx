import { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { cn } from '../lib/utils';

export default function ChatInput({ onSend, disabled }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 bg-white">
      <div className="flex gap-3 items-end">
        <div className="flex-1 relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question..."
            disabled={disabled}
            rows={1}
            className={cn(
              "w-full px-4 py-3 rounded-lg resize-none",
              "bg-gray-100 border border-gray-300",
              "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
              "text-gray-900 placeholder-gray-500",
              "transition-all duration-200",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "max-h-32 overflow-y-auto"
            )}
            style={{
              minHeight: '44px',
              height: 'auto',
            }}
            onInput={(e) => {
              e.target.style.height = 'auto';
              e.target.style.height = e.target.scrollHeight + 'px';
            }}
          />
        </div>
        
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className={cn(
            "flex-shrink-0 p-2.5 rounded-lg transition-all duration-200",
            "bg-blue-600 text-white hover:bg-blue-700",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "transform hover:scale-105 active:scale-95"
          )}
        >
          {disabled ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>
    </form>
  );
}
