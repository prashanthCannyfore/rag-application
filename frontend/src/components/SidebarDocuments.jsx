import { FileText, Trash2, Download } from 'lucide-react';
import { cn, getFileIcon } from '../lib/utils';
import { downloadResume } from '../services/api';

export default function SidebarDocuments({ documents, selectedDoc, onSelectDoc, onDeleteDoc }) {
  const handleDownload = (e, docId) => {
    e.stopPropagation();
    const url = downloadResume(docId);
    window.open(url, '_blank');
  };
  return (
    <div className="flex flex-col h-full bg-slate-950/80">
      {/* Header */}
      <div className="px-4 py-4 border-b border-slate-800/80">
        <h2 className="text-sm md:text-base font-semibold text-slate-50 flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-500" />
          Documents
        </h2>
        <p className="text-xs md:text-sm text-slate-400 mt-1">
          {documents.length} {documents.length === 1 ? 'document' : 'documents'}
        </p>
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        {documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-4">
            <FileText className="w-12 h-12 text-slate-600 mb-3" />
            <p className="text-sm text-slate-400">
              No documents yet
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Upload a document to get started
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className={cn(
                  "group relative flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-slate-950/40",
                  selectedDoc?.id === doc.id
                    ? "bg-blue-600/20 border border-blue-500/30 shadow-md shadow-blue-500/20"
                    : "bg-slate-900/40 border border-slate-800 hover:border-slate-600 hover:bg-slate-900/70"
                )}
                onClick={() => onSelectDoc(doc)}
              >
                <span className="text-2xl flex-shrink-0">
                  {getFileIcon(doc.name)}
                </span>
                <div className="flex-1 min-w-0">
                  <p className={cn(
                    "text-sm font-medium truncate",
                    selectedDoc?.id === doc.id
                      ? "text-blue-400"
                      : "text-slate-200"
                  )}>
                    {doc.name}
                  </p>
                  <p className="text-xs text-slate-400 truncate">
                    {doc.chunks_created || 0} chunks
                  </p>
                </div>
                <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => handleDownload(e, doc.id)}
                    className="p-1.5 rounded-md hover:bg-slate-600/50 text-slate-300 hover:text-white"
                    title="Download document"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteDoc(doc.id);
                    }}
                    className="p-1.5 rounded-md hover:bg-red-900/30 text-red-400 hover:text-red-300"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
