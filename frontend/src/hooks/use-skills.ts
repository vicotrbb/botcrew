import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { SkillSummary, SkillDetail, CreateSkillInput, UpdateSkillInput } from '@/types/skill';
import { getSkills, getSkill, createSkill, updateSkill, deleteSkill } from '@/api/skills';

export function useSkills() {
  return useQuery<SkillSummary[]>({
    queryKey: ['skills'],
    queryFn: () => getSkills(),
  });
}

export function useSkill(id: string | null | undefined) {
  return useQuery<SkillDetail>({
    queryKey: ['skills', id],
    queryFn: () => getSkill(id!),
    enabled: !!id,
  });
}

export function useCreateSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateSkillInput) => createSkill(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['skills'] });
    },
  });
}

export function useUpdateSkill(skillId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateSkillInput) => updateSkill(skillId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['skills', skillId] });
      void queryClient.invalidateQueries({ queryKey: ['skills'] });
    },
  });
}

export function useDeleteSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteSkill(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['skills'] });
    },
  });
}
