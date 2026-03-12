import SourceCard from './SourceCard';

export default function SourcesPanel({ sources }) {
  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="px-4 py-4 border-b border-gray-200 bg-white">
        <h2 className="text-sm font-semibold text-gray-900">
          Sources
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          {sources.length > 0 ? `${sources.length} relevant chunks` : 'No sources yet'}
        </p>
      </div>

      {/* Sources List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {sources.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-4">
            <div className="text-3xl mb-2">📄</div>
            <h3 className="text-sm font-medium text-gray-900 mb-1">
              No sources yet
            </h3>
            <p className="text-xs text-gray-500">
              Ask a question to see relevant sources
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {sources.map((source, index) => (
              <SourceCard key={index} source={source} index={index} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
