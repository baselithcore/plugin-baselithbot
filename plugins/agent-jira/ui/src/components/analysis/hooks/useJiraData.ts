import { useState, useEffect } from 'react';
import { fetchJiraProjects } from '../../../api/client';
import { JiraProject, JiraProjectsResponse } from '../../../types';

export const useJiraData = () => {
  const [jiraProjects, setJiraProjects] = useState<JiraProject[]>([]);
  const [loadingJiraProjects, setLoadingJiraProjects] = useState<boolean>(true);
  const [defaultProjectKey, setDefaultProjectKey] = useState<string>('');
  const [allowedProjectKeys, setAllowedProjectKeys] = useState<string[]>([]);

  useEffect(() => {
    fetchJiraProjects()
      .then((data: JiraProjectsResponse) => {
        setJiraProjects(data.projects);
        setDefaultProjectKey(data.default_project_key || '');
        setAllowedProjectKeys(data.allowed_project_keys || []);
      })
      .catch(console.error)
      .finally(() => setLoadingJiraProjects(false));
  }, []);

  return {
    jiraProjects,
    loadingJiraProjects,
    defaultProjectKey,
    allowedProjectKeys,
  };
};
