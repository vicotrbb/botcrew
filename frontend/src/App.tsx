import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { MainLayout } from './components/layout/MainLayout';
import { DashboardPage } from './pages/dashboard';
import { AgentCreatePage } from './pages/agent-create';
import { AgentDetailPage } from './pages/agent-detail';
import { IntegrationsPage } from './pages/integrations';
import { NotFoundPage } from './pages/not-found';
import { ProjectsPage } from './pages/projects';
import { SecretsPage } from './pages/secrets';
import { SkillsPage } from './pages/skills';
import { TasksPage } from './pages/tasks';
import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<MainLayout />}>
              <Route index element={<Navigate to="/agents" replace />} />
              <Route path="agents" element={<DashboardPage />} />
              <Route path="agents/new" element={<AgentCreatePage />} />
              <Route path="agents/:id" element={<AgentDetailPage />} />
              <Route path="projects" element={<ProjectsPage />} />
              <Route path="tasks" element={<TasksPage />} />
              <Route path="skills" element={<SkillsPage />} />
              <Route path="secrets" element={<SecretsPage />} />
              <Route path="integrations" element={<IntegrationsPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}
