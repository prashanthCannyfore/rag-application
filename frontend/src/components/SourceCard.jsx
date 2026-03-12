import { useState } from 'react';
import { Download, ChevronDown, ChevronUp } from 'lucide-react';
import { downloadResume } from '../services/api';

export default function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false);

  const handleDownload = () => {
    const url = downloadResume(source.document_id);
    window.open(url, '_blank');
  };

  const similarityPercentage = Math.round((source.similarity || 0) * 100);

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-all overflow-hidden">
      <div className="p-3 border-b border-gray-100">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs font-medium text-gray-500">Source {index + 1}</p>
          <div className={`flex-shrink-0 px-2 py-1 rounded text-xs font-medium ${
            similarityPercentage >= 80
              ? 'bg-green-100 text-green-700'
              : similarityPercentage >= 60
              ? 'bg-yellow-100 text-yellow-700'
              : 'bg-gray-100 text-gray-700'
          }`}>
            {similarityPercentage}%
          </div>
        </div>
      </div>

      <div className="p-3">
        <div className={`text-xs text-gray-600 leading-relaxed ${!expanded && 'line-clamp-2'}`}>
          {source.content}
        </div>
        
        {source.content.length > 100 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-2 text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
          >
            {expanded ? (
              <>
                Show less <ChevronUp className="w-3 h-3" />
              </>
            ) : (
              <>
                Show more <ChevronDown className="w-3 h-3" />
              </>
            )}
          </button>
        )}
      </div>

      <div className="p-3 pt-0">
        <button
          onClick={handleDownload}
          className="w-full py-1.5 px-3 rounded text-xs font-medium transition-colors bg-blue-50 text-blue-600 hover:bg-blue-100 flex items-center justify-center gap-1.5"
        >
          <Download className="w-3 h-3" />
          Download
        </button>
      </div>
    </div>
  );
}
