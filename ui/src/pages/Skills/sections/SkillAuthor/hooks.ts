import { useMemo, useState } from 'react';
import type { OpenClawFrontmatterPayload } from '../../../../lib/api';
import {
  DEFAULT_TEMPLATE,
  SLUG_RE,
  type OpenClawOs,
  type SubmitPayload,
  type Surface,
} from './types';

function splitList(raw: string): string[] {
  return raw
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

export interface SkillAuthorForm {
  // basic fields
  slug: string;
  setSlug: (v: string) => void;
  name: string;
  setName: (v: string) => void;
  description: string;
  setDescription: (v: string) => void;
  version: string;
  setVersion: (v: string) => void;
  instructions: string;
  setInstructions: (v: string) => void;
  surfaces: Surface[];
  tagsInput: string;
  setTagsInput: (v: string) => void;
  workspace: string;
  setWorkspace: (v: string) => void;
  overwrite: boolean;
  setOverwrite: (v: boolean) => void;
  // openclaw
  openclawEnabled: boolean;
  setOpenclawEnabled: (v: boolean) => void;
  ocHomepage: string;
  setOcHomepage: (v: string) => void;
  ocUserInvocable: boolean;
  setOcUserInvocable: (v: boolean) => void;
  ocDisableModel: boolean;
  setOcDisableModel: (v: boolean) => void;
  ocDispatch: '' | 'tool';
  setOcDispatch: (v: '' | 'tool') => void;
  ocCommandTool: string;
  setOcCommandTool: (v: string) => void;
  ocCommandArgMode: '' | 'raw';
  setOcCommandArgMode: (v: '' | 'raw') => void;
  ocAlways: boolean;
  setOcAlways: (v: boolean) => void;
  ocEmoji: string;
  setOcEmoji: (v: string) => void;
  ocOs: OpenClawOs[];
  ocPrimaryEnv: string;
  setOcPrimaryEnv: (v: string) => void;
  ocSkillKey: string;
  setOcSkillKey: (v: string) => void;
  ocReqBins: string;
  setOcReqBins: (v: string) => void;
  ocReqAnyBins: string;
  setOcReqAnyBins: (v: string) => void;
  ocReqEnv: string;
  setOcReqEnv: (v: string) => void;
  ocReqConfig: string;
  setOcReqConfig: (v: string) => void;
  // derived
  tags: string[];
  openclawPayload: OpenClawFrontmatterPayload | null;
  slugClean: string;
  slugValid: boolean;
  slugCollides: boolean;
  dispatchConsistent: boolean;
  canSubmit: boolean;
  // handlers
  toggleSurface: (surface: Surface) => void;
  toggleOcOs: (value: OpenClawOs) => void;
  buildPayload: () => SubmitPayload;
  reset: () => void;
}

export function useSkillAuthorForm(installedSlugs: Set<string>, pending: boolean): SkillAuthorForm {
  const [slug, setSlug] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [version, setVersion] = useState('0.1.0');
  const [instructions, setInstructions] = useState(DEFAULT_TEMPLATE);
  const [surfaces, setSurfaces] = useState<Surface[]>(['chat']);
  const [tagsInput, setTagsInput] = useState('');
  const [workspace, setWorkspace] = useState<string>('');
  const [overwrite, setOverwrite] = useState(false);

  const [openclawEnabled, setOpenclawEnabled] = useState(false);
  const [ocHomepage, setOcHomepage] = useState('');
  const [ocUserInvocable, setOcUserInvocable] = useState(true);
  const [ocDisableModel, setOcDisableModel] = useState(false);
  const [ocDispatch, setOcDispatch] = useState<'' | 'tool'>('');
  const [ocCommandTool, setOcCommandTool] = useState('');
  const [ocCommandArgMode, setOcCommandArgMode] = useState<'' | 'raw'>('');
  const [ocAlways, setOcAlways] = useState(false);
  const [ocEmoji, setOcEmoji] = useState('');
  const [ocOs, setOcOs] = useState<OpenClawOs[]>([]);
  const [ocPrimaryEnv, setOcPrimaryEnv] = useState('');
  const [ocSkillKey, setOcSkillKey] = useState('');
  const [ocReqBins, setOcReqBins] = useState('');
  const [ocReqAnyBins, setOcReqAnyBins] = useState('');
  const [ocReqEnv, setOcReqEnv] = useState('');
  const [ocReqConfig, setOcReqConfig] = useState('');

  const tags = useMemo(
    () =>
      tagsInput
        .split(',')
        .map((tag) => tag.trim().toLowerCase())
        .filter((tag) => tag.length > 0 && tag.length <= 48),
    [tagsInput]
  );

  const openclawPayload = useMemo<OpenClawFrontmatterPayload | null>(() => {
    if (!openclawEnabled) return null;
    return {
      homepage: ocHomepage.trim() || null,
      user_invocable: ocUserInvocable,
      disable_model_invocation: ocDisableModel,
      command_dispatch: ocDispatch || null,
      command_tool: ocCommandTool.trim() || null,
      command_arg_mode: ocCommandArgMode || null,
      always: ocAlways,
      emoji: ocEmoji.trim() || null,
      os: [...ocOs],
      primary_env: ocPrimaryEnv.trim() || null,
      skill_key: ocSkillKey.trim() || null,
      requires: {
        bins: splitList(ocReqBins),
        any_bins: splitList(ocReqAnyBins),
        env: splitList(ocReqEnv),
        config: splitList(ocReqConfig),
      },
      install: [],
    };
  }, [
    openclawEnabled,
    ocHomepage,
    ocUserInvocable,
    ocDisableModel,
    ocDispatch,
    ocCommandTool,
    ocCommandArgMode,
    ocAlways,
    ocEmoji,
    ocOs,
    ocPrimaryEnv,
    ocSkillKey,
    ocReqBins,
    ocReqAnyBins,
    ocReqEnv,
    ocReqConfig,
  ]);

  const slugClean = slug.trim().toLowerCase();
  const slugValid = slugClean === '' || SLUG_RE.test(slugClean);
  const slugCollides = slugClean !== '' && installedSlugs.has(slugClean);
  const dispatchConsistent =
    !openclawEnabled || ocDispatch !== 'tool' || ocCommandTool.trim().length > 0;

  const canSubmit =
    !pending &&
    slugClean !== '' &&
    slugValid &&
    name.trim() !== '' &&
    description.trim() !== '' &&
    instructions.trim() !== '' &&
    surfaces.length > 0 &&
    dispatchConsistent &&
    (!slugCollides || overwrite);

  const toggleSurface = (surface: Surface) => {
    setSurfaces((prev) =>
      prev.includes(surface) ? prev.filter((item) => item !== surface) : [...prev, surface]
    );
  };

  const toggleOcOs = (value: OpenClawOs) => {
    setOcOs((prev) =>
      prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value]
    );
  };

  const reset = () => {
    setSlug('');
    setName('');
    setDescription('');
    setVersion('0.1.0');
    setInstructions(DEFAULT_TEMPLATE);
    setSurfaces(['chat']);
    setTagsInput('');
    setWorkspace('');
    setOverwrite(false);
    setOpenclawEnabled(false);
    setOcHomepage('');
    setOcUserInvocable(true);
    setOcDisableModel(false);
    setOcDispatch('');
    setOcCommandTool('');
    setOcCommandArgMode('');
    setOcAlways(false);
    setOcEmoji('');
    setOcOs([]);
    setOcPrimaryEnv('');
    setOcSkillKey('');
    setOcReqBins('');
    setOcReqAnyBins('');
    setOcReqEnv('');
    setOcReqConfig('');
  };

  const buildPayload = (): SubmitPayload => ({
    slug: slugClean,
    name: name.trim(),
    description: description.trim(),
    version: version.trim() || '0.1.0',
    instructions,
    surfaces,
    tags,
    workspace: workspace || null,
    overwrite,
    openclaw: openclawPayload,
  });

  return {
    slug,
    setSlug,
    name,
    setName,
    description,
    setDescription,
    version,
    setVersion,
    instructions,
    setInstructions,
    surfaces,
    tagsInput,
    setTagsInput,
    workspace,
    setWorkspace,
    overwrite,
    setOverwrite,
    openclawEnabled,
    setOpenclawEnabled,
    ocHomepage,
    setOcHomepage,
    ocUserInvocable,
    setOcUserInvocable,
    ocDisableModel,
    setOcDisableModel,
    ocDispatch,
    setOcDispatch,
    ocCommandTool,
    setOcCommandTool,
    ocCommandArgMode,
    setOcCommandArgMode,
    ocAlways,
    setOcAlways,
    ocEmoji,
    setOcEmoji,
    ocOs,
    ocPrimaryEnv,
    setOcPrimaryEnv,
    ocSkillKey,
    setOcSkillKey,
    ocReqBins,
    setOcReqBins,
    ocReqAnyBins,
    setOcReqAnyBins,
    ocReqEnv,
    setOcReqEnv,
    ocReqConfig,
    setOcReqConfig,
    tags,
    openclawPayload,
    slugClean,
    slugValid,
    slugCollides,
    dispatchConsistent,
    canSubmit,
    toggleSurface,
    toggleOcOs,
    buildPayload,
    reset,
  };
}
