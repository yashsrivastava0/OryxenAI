import type { StructuredProfileVM } from "../data/adapters/discovery";

interface ExtractedProfileRailProps {
  profile: StructuredProfileVM;
}

function isProfileEmpty(profile: StructuredProfileVM): boolean {
  return (
    !profile.name &&
    !profile.currentTitle &&
    profile.skills.length === 0 &&
    profile.experience.length === 0 &&
    profile.projects.length === 0 &&
    profile.education.length === 0 &&
    profile.links.length === 0
  );
}

/**
 * Renders the StructuredProfile facts the Discovery model already extracts
 * on every brief (agents/discovery/schemas.py::StructuredProfile) — skills,
 * work history, projects, education, links. Previously these were parsed
 * server-side and shipped to the client, then discarded: DiscoveryStage only
 * ever rendered brief.markdown / user_summary. This is the evidence trail —
 * "here is what we found in what you gave us" — sitting beside the brief so
 * approving it feels grounded in fact, not a black box.
 */
export function ExtractedProfileRail({ profile }: ExtractedProfileRailProps) {
  if (isProfileEmpty(profile)) return null;

  return (
    <aside className="extracted-profile-rail" aria-label="Facts extracted from your material">
      <p className="eyebrow">Extracted from your material</p>
      {(profile.name || profile.currentTitle) && (
        <div className="profile-identity">
          {profile.name && <strong>{profile.name}</strong>}
          {profile.currentTitle && <span>{profile.currentTitle}</span>}
          {profile.location && <span className="profile-location">{profile.location}</span>}
        </div>
      )}

      {profile.skills.length > 0 && (
        <div className="profile-fact-group">
          <p className="profile-fact-label">Skills · {profile.skills.length}</p>
          <ul className="profile-skill-tags oxa-stagger">
            {profile.skills.map((skill) => (
              <li key={skill} className="profile-skill-tag">{skill}</li>
            ))}
          </ul>
        </div>
      )}

      {profile.experience.length > 0 && (
        <div className="profile-fact-group">
          <p className="profile-fact-label">Experience · {profile.experience.length}</p>
          <ol className="profile-experience-list oxa-stagger">
            {profile.experience.map((entry, idx) => (
              <li key={`${entry.organization}-${idx}`} className="profile-experience-card">
                <div className="profile-experience-head">
                  <strong>{entry.role || "Role"}</strong>
                  {entry.dates && <span className="profile-dates">{entry.dates}</span>}
                </div>
                {entry.organization && <p className="profile-org">{entry.organization}</p>}
                {entry.highlights.length > 0 && (
                  <ul className="profile-highlights">
                    {entry.highlights.slice(0, 2).map((highlight, hIdx) => (
                      <li key={hIdx}>{highlight}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}

      {profile.projects.length > 0 && (
        <div className="profile-fact-group">
          <p className="profile-fact-label">Projects · {profile.projects.length}</p>
          <ul className="profile-project-list oxa-stagger">
            {profile.projects.map((project, idx) => (
              <li key={`${project.name}-${idx}`} className="profile-project-card">
                <strong>{project.name || "Untitled project"}</strong>
                {project.summary && <p>{project.summary}</p>}
                {project.tech.length > 0 && (
                  <p className="profile-project-tech">{project.tech.join(" · ")}</p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {profile.education.length > 0 && (
        <div className="profile-fact-group">
          <p className="profile-fact-label">Education · {profile.education.length}</p>
          <ul className="profile-education-list">
            {profile.education.map((entry, idx) => (
              <li key={`${entry.institution}-${idx}`}>
                <strong>{entry.credential || entry.institution}</strong>
                {entry.institution && entry.credential && <span> · {entry.institution}</span>}
                {entry.dates && <span className="profile-dates"> · {entry.dates}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {profile.links.length > 0 && (
        <div className="profile-fact-group">
          <p className="profile-fact-label">Links · {profile.links.length}</p>
          <ul className="profile-link-list">
            {profile.links.map((link, idx) => (
              <li key={idx}>
                <a href={link.url} target="_blank" rel="noopener noreferrer">{link.label || link.url}</a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}
