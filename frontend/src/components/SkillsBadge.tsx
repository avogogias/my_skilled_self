/**
 * SkillsBadge — displays registered agent skills in the sidebar/header.
 */

import React, { useEffect, useState } from 'react';
import { getSkills } from '@/services/api';
import type { SkillInfo } from '@/types';

export const SkillsBadge: React.FC = () => {
  const [skills, setSkills] = useState<SkillInfo[]>([]);

  useEffect(() => {
    getSkills()
      .then((r) => setSkills(r.skills))
      .catch(() => {});
  }, []);

  if (!skills.length) return null;

  return (
    <div className="skills-badge">
      <span className="skills-label">Active skills:</span>
      {skills.map((s) => (
        <span key={s.name} className="skill-chip" title={s.description}>
          {s.icon} {s.name.replace(/_/g, ' ')}
        </span>
      ))}
    </div>
  );
};
