import type { SkillSummary, SkillDetail, CreateSkillInput, UpdateSkillInput } from '@/types/skill';
import { fetchOne, fetchList, postJSON, patchJSON, deleteJSON } from '@/api/client';

export async function getSkills(): Promise<SkillSummary[]> {
  return fetchList<Omit<SkillSummary, 'id'>>('/skills');
}

export async function getSkill(id: string): Promise<SkillDetail> {
  return fetchOne<Omit<SkillDetail, 'id'>>(`/skills/${id}`);
}

export async function createSkill(input: CreateSkillInput): Promise<SkillDetail> {
  return postJSON<Omit<SkillDetail, 'id'>>('/skills', input, 'skills');
}

export async function updateSkill(id: string, input: UpdateSkillInput): Promise<SkillDetail> {
  return patchJSON<Omit<SkillDetail, 'id'>>(`/skills/${id}`, input, 'skills');
}

export async function deleteSkill(id: string): Promise<void> {
  return deleteJSON(`/skills/${id}`);
}
