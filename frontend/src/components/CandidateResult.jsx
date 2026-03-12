import { Download } from 'lucide-react';

export default function CandidateResult({ candidate, onDownload }) {
  const isPDF = candidate.is_pdf === true;
  const hasResume = candidate.has_resume === true;
  const resumeDocId = candidate.resume_document_id || candidate.document_id;

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
        <h3 style={{
          fontSize: '16px',
          fontWeight: '600',
          margin: '0 0 4px 0',
          color: '#1f2937'
        }}>
          {candidate.name || candidate.filename || 'Unknown'}
        </h3>
        {candidate.role && (
          <p style={{
            fontSize: '14px',
            color: '#6b7280',
            margin: '0 0 4px 0'
          }}>
            {candidate.role}
          </p>
        )}
      </div>

      {/* Details Grid */}
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

      {/* Match Score */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '12px',
        paddingBottom: '12px',
        borderBottom: '1px solid #f3f4f6'
      }}>
        <span style={{ fontSize: '13px', color: '#6b7280' }}>Match Score:</span>
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
              width: `${Math.min(candidate.match_score || 0, 100)}%`,
              height: '100%',
              backgroundColor: candidate.match_score >= 80 ? '#10b981' : candidate.match_score >= 60 ? '#f59e0b' : '#ef4444'
            }} />
          </div>
          <span style={{
            fontSize: '13px',
            fontWeight: '600',
            color: '#1f2937',
            minWidth: '35px'
          }}>
            {Math.round(candidate.match_score || 0)}%
          </span>
        </div>
      </div>

      {/* Resume Status and Download Button */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        {isPDF ? (
          <span style={{
            fontSize: '12px',
            color: '#059669',
            fontWeight: '500'
          }}>
            ✓ PDF Resume
          </span>
        ) : (
          <span style={{
            fontSize: '12px',
            color: hasResume ? '#059669' : '#dc2626',
            fontWeight: '500'
          }}>
            {hasResume ? '✓ Resume Matched' : '✗ No Resume'}
          </span>
        )}

        {/* Download Button - Only show for actual PDF resumes */}
        {isPDF && (
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
            Download PDF
          </button>
        )}
      </div>
    </div>
  );
}
