import { Card } from '../../../components/ui';
import { Field } from './_shared';

export type IdentityStepProps = {
  name: string;
  setName: (v: string) => void;
  environment: string;
  setEnvironment: (v: string) => void;
  owner: string;
  setOwner: (v: string) => void;
  tags: string;
  setTags: (v: string) => void;
  description: string;
  setDescription: (v: string) => void;
};

export function IdentityStep(p: IdentityStepProps) {
  return (
    <Card title="Identity & ownership" subtitle="Help your team find this later">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Display name">
          <input
            value={p.name}
            onChange={(e) => p.setName(e.target.value)}
            placeholder="Production API gateway"
            className="ra-input"
          />
        </Field>
        <Field label="Environment">
          <select
            value={p.environment}
            onChange={(e) => p.setEnvironment(e.target.value)}
            className="ra-select"
          >
            <option value="production">production</option>
            <option value="staging">staging</option>
            <option value="dev">dev</option>
            <option value="qa">qa</option>
          </select>
        </Field>
        <Field label="Owner team / email">
          <input
            value={p.owner}
            onChange={(e) => p.setOwner(e.target.value)}
            placeholder="platform-security@acme.com"
            className="ra-input"
          />
        </Field>
        <Field label="Tags (comma-separated)">
          <input
            value={p.tags}
            onChange={(e) => p.setTags(e.target.value)}
            placeholder="pci, public, tier-1"
            className="ra-input"
          />
        </Field>
        <div className="sm:col-span-2">
          <Field label="Description (optional)">
            <textarea
              value={p.description}
              onChange={(e) => p.setDescription(e.target.value)}
              placeholder="What is this target? Any context reviewers should know."
              rows={3}
              className="ra-input min-h-[88px] resize-y"
            />
          </Field>
        </div>
      </div>
    </Card>
  );
}
