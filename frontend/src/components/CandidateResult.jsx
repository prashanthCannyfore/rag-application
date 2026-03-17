import { useState } from 'react';
import { Download, ChevronDown, ChevronUp, Mail, Phone, MapPin, Briefcase, GraduationCap, Award, Building2, Clock } from 'lucide-react';

export default function CandidateResult({ candidate, onDownload }) {
  const [expanded, setExpanded] = useState(true);  // expanded by default
  const isFromCSV = candidate.source === 'csv';
  const hasResume = candidate.has_resume === true;
  const resumeDocId = candidate.resume_document_id || candidate.document_id;
  const matchScore = candidate.combined_score || candidate.match_score || 0;
  const scoreColor = matchScore >= 80 ? '#10b981' : matchScore >= 60 ? '#f59e0b' : '#ef4444';

  // Count available extra details for the toggle label
  const detailCount = [
    candidate.summary, candidate.email, candidate.phone,
    candidate.education?.length, candidate.certifications?.length,
    candidate.companies?.length, candidate.notice_period
  ].filter(Boolean).length;

  const Tag = ({ children, color = '#f3f4f6', textColor = '#374151' }) => (
    <span style={{
      fontSize: '11px', padding: '2px 8px', borderRadius: '12px',
      backgroundColor: color, color: textColor, fontWeight: '500', whiteSpace: 'nowrap'
    }}>
      {children}
    </span>
  );

  const InfoRow = ({ icon: Icon, label, value }) => {
    if (!value) return null;
    return (
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', fontSize: '13px' }}>
        <Icon size={14} style={{ color: '#9ca3af', marginTop: '2px', flexShrink: 0 }} />
        <div>
          <span style={{ color: '#6b7280' }}>{label}: </span>
          <span style={{ color: '#1f2937', fontWeight: '500' }}>{value}</span>
        </div>
      </div>
    );
  };

  return (
    <div style={{
      marginBottom: '12px', backgroundColor: '#fff',
      border: '1px solid #e5e7eb', borderRadius: '10px', overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{ padding: '14px 16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '4px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: '700', margin: 0, color: '#111827' }}>
                {candidate.name || candidate.filename || 'Unknown'}
              </h3>
              <Tag color={isFromCSV ? '#dcfce7' : '#dbeafe'} textColor={isFromCSV ? '#166534' : '#1d4ed8'}>
                {isFromCSV ? 'CSV + Resume' : 'Resume Only'}
              </Tag>
              {hasResume && <Tag color="#fef3c7" textColor="#92400e">Resume</Tag>}
            </div>

            {candidate.role && (
              <p style={{ fontSize: '13px', color: '#6b7280', margin: '0 0 8px 0' }}>{candidate.role}</p>
            )}

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
              {candidate.location && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: '#6b7280' }}>
                  <MapPin size={12} /> {candidate.location}
                </div>
              )}
              {candidate.experience && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: '#6b7280' }}>
                  <Briefcase size={12} /> {candidate.experience}
                </div>
              )}
              {candidate.cost && (
                <div style={{ fontSize: '12px', color: '#6b7280' }}>
                  💰 ₹{candidate.cost}
                </div>
              )}
              {candidate.notice_period && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: '#6b7280' }}>
                  <Clock size={12} /> {candidate.notice_period}
                </div>
              )}
            </div>
          </div>

          {/* Score circle */}
          <div style={{ textAlign: 'center', marginLeft: '12px', flexShrink: 0 }}>
            <div style={{
              width: '52px', height: '52px', borderRadius: '50%',
              border: `3px solid ${scoreColor}`, display: 'flex',
              alignItems: 'center', justifyContent: 'center'
            }}>
              <span style={{ fontSize: '14px', fontWeight: '700', color: scoreColor }}>
                {Math.round(matchScore)}%
              </span>
            </div>
            <span style={{ fontSize: '10px', color: '#9ca3af', marginTop: '2px', display: 'block' }}>match</span>
          </div>
        </div>

        {/* Skills */}
        {candidate.skills && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '10px' }}>
            {candidate.skills.split(',').slice(0, 8).map((skill, i) => (
              <Tag key={i}>{skill.trim()}</Tag>
            ))}
            {candidate.skills.split(',').length > 8 && (
              <Tag color="#e0e7ff" textColor="#4338ca">+{candidate.skills.split(',').length - 8} more</Tag>
            )}
          </div>
        )}
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div style={{ padding: '14px 16px', backgroundColor: '#fafafa', borderTop: '1px solid #f3f4f6' }}>
          {candidate.summary && (
            <div style={{ marginBottom: '14px', padding: '10px', backgroundColor: '#fff', borderRadius: '6px', border: '1px solid #e5e7eb' }}>
              <p style={{ fontSize: '11px', fontWeight: '600', color: '#6b7280', margin: '0 0 4px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Summary</p>
              <p style={{ fontSize: '13px', color: '#374151', margin: 0, lineHeight: '1.5' }}>{candidate.summary}</p>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div>
              <p style={{ fontSize: '11px', fontWeight: '600', color: '#6b7280', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Contact</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <InfoRow icon={Mail} label="Email" value={candidate.email} />
                <InfoRow icon={Phone} label="Phone" value={candidate.phone} />
                <InfoRow icon={MapPin} label="Location" value={candidate.location} />
              </div>
            </div>

            <div>
              <p style={{ fontSize: '11px', fontWeight: '600', color: '#6b7280', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Work Info</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <InfoRow icon={Briefcase} label="Experience" value={candidate.experience} />
                <InfoRow icon={Clock} label="Notice Period" value={candidate.notice_period} />
                <InfoRow icon={Briefcase} label="Cost" value={candidate.cost ? `₹${candidate.cost}` : null} />
              </div>
            </div>

            {candidate.education?.length > 0 && (
              <div>
                <p style={{ fontSize: '11px', fontWeight: '600', color: '#6b7280', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Education
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {candidate.education.map((edu, i) => (
                    <Tag key={i} color="#ede9fe" textColor="#5b21b6">{edu}</Tag>
                  ))}
                </div>
              </div>
            )}

            {candidate.certifications?.length > 0 && (
              <div>
                <p style={{ fontSize: '11px', fontWeight: '600', color: '#6b7280', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Certifications
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {candidate.certifications.map((cert, i) => (
                    <Tag key={i} color="#fef3c7" textColor="#92400e">{cert}</Tag>
                  ))}
                </div>
              </div>
            )}

            {candidate.companies?.length > 0 && (
              <div style={{ gridColumn: '1 / -1' }}>
                <p style={{ fontSize: '11px', fontWeight: '600', color: '#6b7280', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Previous Companies
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {candidate.companies.map((company, i) => (
                    <Tag key={i} color="#f0fdf4" textColor="#166534">{company}</Tag>
                  ))}
                </div>
              </div>
            )}

            {candidate.match_details?.reasoning?.length > 0 && (
              <div style={{ gridColumn: '1 / -1' }}>
                <p style={{ fontSize: '11px', fontWeight: '600', color: '#6b7280', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Match Reasoning</p>
                <ul style={{ margin: 0, paddingLeft: '16px' }}>
                  {candidate.match_details.reasoning.map((reason, i) => (
                    <li key={i} style={{ fontSize: '12px', color: '#374151', marginBottom: '2px' }}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}

            {candidate.resume_content_preview && (
              <div style={{ gridColumn: '1 / -1' }}>
                <p style={{ fontSize: '11px', fontWeight: '600', color: '#6b7280', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Resume Preview</p>
                <div style={{ padding: '10px', backgroundColor: '#fff', borderRadius: '6px', border: '1px solid #e5e7eb', borderLeft: '3px solid #3b82f6' }}>
                  <p style={{ fontSize: '12px', color: '#374151', margin: 0, lineHeight: '1.6', fontStyle: 'italic' }}>
                    {candidate.resume_content_preview}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{
        padding: '10px 16px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', borderTop: '1px solid #f3f4f6'
      }}>
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            fontSize: '12px', color: '#2563eb', background: 'none',
            border: '1px solid #dbeafe', borderRadius: '5px',
            cursor: 'pointer', padding: '4px 10px', fontWeight: '500'
          }}
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {expanded ? 'Collapse' : `Full Profile${detailCount > 0 ? ` (${detailCount} details)` : ''}`}
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: hasResume ? '#059669' : '#dc2626', fontWeight: '500' }}>
            {hasResume ? '✓ Resume Available' : '✗ No Resume'}
          </span>
          {hasResume && resumeDocId && (
            <button
              onClick={() => onDownload(resumeDocId)}
              style={{
                padding: '5px 12px', backgroundColor: '#2563eb', color: '#fff',
                border: 'none', borderRadius: '5px', cursor: 'pointer',
                fontSize: '12px', fontWeight: '500', display: 'flex',
                alignItems: 'center', gap: '5px'
              }}
            >
              <Download size={13} /> Download Resume
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
