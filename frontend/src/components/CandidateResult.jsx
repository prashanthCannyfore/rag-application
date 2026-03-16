import { Download } from 'lucide-react';

export default function CandidateResult({ candidate, onDownload }) {
  const isFromCSV = candidate.source === 'csv';
  const isFromRAG = candidate.source === 'rag_resume';
  const hasResume = candidate.has_resume === true;
  const resumeDocId = candidate.resume_document_id || candidate.document_id;
  const matchScore = candidate.combined_score || candidate.match_score || 0;

  return (
    <div style={{
      padding: '16px',
      marginBottom: '12px',
      backgroundColor: '#fff',
      border: '1px solid #e0e0e0',
      borderRadius: '8px'
    }}>
      {/* Candidate Name and Role */}
      <div style={{ marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <h3 style={{
            fontSize: '16px',
            fontWeight: '600',
            margin: '0',
            color: '#1f2937'
          }}>
            {candidate.name || candidate.filename || 'Unknown'}
          </h3>
          {/* Source Badge */}
          <span style={{
            fontSize: '10px',
            fontWeight: '500',
            padding: '2px 6px',
            borderRadius: '4px',
            backgroundColor: isFromCSV ? '#dcfce7' : '#dbeafe',
            color: isFromCSV ? '#166534' : '#1d4ed8'
          }}>
            {isFromCSV ? 'CSV + Resume' : 'Resume Only'}
          </span>
        </div>
        {candidate.role && (
          <p style={{
            fontSize: '14px',
            color: '#6b7280',
            margin: '0'
          }}>
            {candidate.role}
          </p>
        )}
        {candidate.filename && !candidate.role && (
          <p style={{
            fontSize: '12px',
            color: '#9ca3af',
            margin: '0',
            fontStyle: 'italic'
          }}>
            {candidate.filename}
          </p>
        )}
      </div>

      {/* Details Grid - Only show for CSV candidates */}
      {isFromCSV && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
          marginBottom: '12px',
          fontSize: '13px'
        }}>
          {candidate.location && (
            <div>
              <span style={{ color: '#6b7280', fontWeight: '500' }}>Location:</span>
              <p style={{ margin: '2px 0 0 0', color: '#1f2937' }}>{candidate.location}</p>
            </div>
          )}
          {candidate.cost && (
            <div>
              <span style={{ color: '#6b7280', fontWeight: '500' }}>Cost:</span>
              <p style={{ margin: '2px 0 0 0', color: '#1f2937' }}>₹{candidate.cost}</p>
            </div>
          )}
          {candidate.skills && (
            <div style={{ gridColumn: '1 / -1' }}>
              <span style={{ color: '#6b7280', fontWeight: '500' }}>Skills:</span>
              <p style={{ margin: '2px 0 0 0', color: '#1f2937' }}>{candidate.skills}</p>
            </div>
          )}
        </div>
      )}

      {/* Match Details for RAG-only candidates */}
      {isFromRAG && candidate.match_details?.matches && (
        <div style={{ marginBottom: '12px' }}>
          <span style={{ fontSize: '13px', color: '#6b7280', fontWeight: '500' }}>Matching Skills:</span>
          <div style={{ marginTop: '4px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {candidate.match_details.matches.map((match, idx) => (
              <span key={idx} style={{
                fontSize: '11px',
                padding: '2px 6px',
                backgroundColor: '#f3f4f6',
                color: '#374151',
                borderRadius: '3px'
              }}>
                {match}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Match Score */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '12px',
        paddingBottom: '12px',
        borderBottom: '1px solid #f3f4f6'
      }}>
        <span style={{ fontSize: '13px', color: '#6b7280' }}>
          {isFromCSV ? 'Combined Score:' : 'Match Score:'}
        </span>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <div style={{
            width: '100px',
            height: '6px',
            backgroundColor: '#e5e7eb',
            borderRadius: '3px',
            overflow: 'hidden'
          }}>
            <div style={{
              width: `${Math.min(matchScore, 100)}%`,
              height: '100%',
              backgroundColor: matchScore >= 80 ? '#10b981' : matchScore >= 60 ? '#f59e0b' : '#ef4444'
            }} />
          </div>
          <span style={{
            fontSize: '13px',
            fontWeight: '600',
            color: '#1f2937',
            minWidth: '35px'
          }}>
            {Math.round(matchScore)}%
          </span>
        </div>
      </div>

      {/* Resume Status and Download Button */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <span style={{
          fontSize: '12px',
          color: hasResume ? '#059669' : '#dc2626',
          fontWeight: '500'
        }}>
          {hasResume ? '✓ Resume Available' : '✗ No Resume'}
        </span>

        {/* Download Button - Show for any candidate with resume */}
        {hasResume && resumeDocId && (
          <button
            onClick={() => onDownload(resumeDocId)}
            style={{
              padding: '6px 12px',
              backgroundColor: '#dbeafe',
              color: '#2563eb',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: '500',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => e.target.style.backgroundColor = '#bfdbfe'}
            onMouseLeave={(e) => e.target.style.backgroundColor = '#dbeafe'}
          >
            <Download size={14} />
            Download Resume
          </button>
        )}
      </div>

      {/* Resume Preview for RAG candidates */}
      {isFromRAG && candidate.resume_content_preview && (
        <div style={{
          marginTop: '12px',
          padding: '8px',
          backgroundColor: '#f9fafb',
          borderRadius: '4px',
          borderLeft: '3px solid #3b82f6'
        }}>
          <span style={{ fontSize: '11px', color: '#6b7280', fontWeight: '500' }}>Resume Preview:</span>
          <p style={{
            fontSize: '11px',
            color: '#374151',
            margin: '4px 0 0 0',
            lineHeight: '1.4'
          }}>
            {candidate.resume_content_preview}
          </p>
        </div>
      )}
    </div>
  );
}
