export interface SkillSummary {
  id: string;
  name: string;
  description: string;
  body: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Skills don't have a separate detail type; SkillSummary includes body
export type SkillDetail = SkillSummary;

export interface CreateSkillInput {
  name: string;
  description: string;
  body: string;
}

export interface UpdateSkillInput {
  name?: string;
  description?: string;
  body?: string;
}
