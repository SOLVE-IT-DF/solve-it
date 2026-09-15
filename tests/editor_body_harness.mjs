/* Exercises the issue-body builder in reporting_scripts/assets/editor.js
   outside a browser, and prints the result as JSON for test_editor_body.py to
   check against the issue parsers.

   Only the part of editor.js above the form rendering is loaded: that is the
   pure logic — field specs, change detection and body construction — and it
   touches no DOM. Loading it this way means the test exercises the same source
   the page ships, not a copy of it. */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(path.join(here, '..', 'reporting_scripts', 'assets', 'editor.js'), 'utf8');
const marker = '/* ── Form rendering ──';
const cut = source.indexOf(marker);
if (cut < 0) throw new Error('editor.js no longer has the form-rendering marker the harness splits on');

// A small knowledge base, so editorProblems() can tell a known ID from an
// unknown one.
const KNOWN_TECHNIQUES = [{ id: 'DFT-1044', name: 'Known subtechnique' }, { id: 'DFT-1099', name: 'Known technique' }];
const KNOWN_WEAKNESSES = [{ id: 'DFW-1001', name: 'Known weakness one' }, { id: 'DFW-1002', name: 'Known weakness two' }];
const KNOWN_MITIGATIONS = [{ id: 'DFM-1001', name: 'Known mitigation' }];
globalThis.DB = { techniques: KNOWN_TECHNIQUES, weaknesses: KNOWN_WEAKNESSES, mitigations: KNOWN_MITIGATIONS };
globalThis.TMap = Object.fromEntries(KNOWN_TECHNIQUES.map(t => [t.id, t]));
globalThis.WMap = Object.fromEntries(KNOWN_WEAKNESSES.map(w => [w.id, w]));
globalThis.MMap = Object.fromEntries(KNOWN_MITIGATIONS.map(m => [m.id, m]));
globalThis.CiteMap = {};

const api = new Function(source.slice(0, cut) + `
  return {
    EDIT_SPECS,
    build(type, item, mutate) {
      const spec = EDIT_SPECS[type];
      const state = { type, item, values: {}, original: {}, notes: '', reviewing: false };
      for (const field of spec.fields) {
        state.original[field.key] = editorReadValue(item, field);
        state.values[field.key] = editorReadValue(item, field);
      }
      editorState = state;
      mutate(state);
      const sections = editorChangedSections();
      const url = editorBuildUrl(sections);
      return { body: editorBuildBody(sections), url, sections, problems: editorProblems(sections, url) };
    },
  };
`)();

const TECHNIQUE = {
  id: 'DFT-1043',
  name: 'Read bitstream',
  description: 'Original description.',
  details: 'Original details.',
  synonyms: ['imaging', 'acquisition'],
  examples: ['dd'],
  subtechniques: ['DFT-1044'],
  weaknesses: ['DFW-1001', 'DFW-1002'],
  CASE_input_classes: ['https://ontology.unifiedcyberontology.org/uco/observable/Device'],
  CASE_output_classes: ['https://ontology.unifiedcyberontology.org/uco/observable/File'],
  references: [{ DFCite_id: 'DFCite-1001', relevance_summary_280: 'Original relevance.' }],
};

const WEAKNESS = {
  id: 'DFW-1001',
  name: 'Original weakness name',
  description: '',
  categories: ['ASTM_INCOMP'],
  mitigations: ['DFM-1001'],
  references: [],
};

const MITIGATION = {
  id: 'DFM-1001',
  name: 'Original mitigation name',
  description: '',
  technique: 'DFT-1050',
  references: [],
};

const cases = {};

cases.technique_scalars = api.build('technique', TECHNIQUE, s => {
  s.values.name = 'Read bitstream from a device';
  s.values.description = 'A revised description with a [DFCite-1001] citation.';
});

cases.technique_clear_synonyms = api.build('technique', TECHNIQUE, s => {
  s.values.synonyms = [];
});

cases.technique_lists = api.build('technique', TECHNIQUE, s => {
  s.values.weaknesses = ['DFW-1001', 'DFW-9999'];
  s.values.CASE_output_classes = [
    'https://ontology.unifiedcyberontology.org/uco/observable/File',
    'https://ontology.unifiedcyberontology.org/uco/observable/RasterPicture',
  ];
});

cases.technique_references = api.build('technique', TECHNIQUE, s => {
  s.values.references = [
    { id: 'DFCite-1001', relevance: 'A revised relevance summary.' },
    { id: 'DFCite-1002', relevance: 'Newly added.' },
  ];
});

cases.technique_clear_references = api.build('technique', TECHNIQUE, s => {
  s.values.references = [];
});

cases.technique_untouched = api.build('technique', TECHNIQUE, () => {});

cases.technique_notes_and_new_weaknesses = api.build('technique', TECHNIQUE, s => {
  s.values._new_weaknesses = 'Imaging may miss data in hidden areas';
  s.notes = 'Proposing a new ontology class for firmware regions.';
});

cases.technique_heading_in_value = api.build('technique', TECHNIQUE, s => {
  s.values.details = 'Line one\n### Weakness IDs\nDFW-9999';
});

cases.weakness_categories = api.build('weakness', WEAKNESS, s => {
  s.values.categories = ['ASTM_INCOMP', 'ASTM_MISINT'];
});

cases.weakness_clear_mitigations = api.build('weakness', WEAKNESS, s => {
  s.values.mitigations = [];
});

cases.mitigation_set_link = api.build('mitigation', MITIGATION, s => {
  s.values.technique = { action: 'set', id: 'DFT-1099' };
});

cases.mitigation_remove_link = api.build('mitigation', MITIGATION, s => {
  s.values.technique = { action: 'remove', id: '' };
});

cases.mitigation_keep_link = api.build('mitigation', MITIGATION, s => {
  s.values.name = 'A revised mitigation name';
});

// ── Validation cases ─────────────────────────────────────────────────
cases.problem_fence_in_value = api.build('technique', TECHNIQUE, s => {
  s.values.details = 'Some text\n```\ncode\n```';
});

cases.problem_relevance_too_long = api.build('technique', TECHNIQUE, s => {
  s.values.references = [{ id: 'DFCite-1001', relevance: 'x'.repeat(281) }];
});

cases.problem_unknown_weakness = api.build('technique', TECHNIQUE, s => {
  s.values.weaknesses = ['DFW-1001', 'DFW-9999'];
});

cases.problem_empty_name = api.build('technique', TECHNIQUE, s => {
  s.values.name = '   ';
});

cases.problem_link_without_id = api.build('mitigation', MITIGATION, s => {
  s.values.technique = { action: 'set', id: '' };
});

cases.problem_url_too_long = api.build('technique', TECHNIQUE, s => {
  s.values.details = 'long '.repeat(2000);
});

cases.clean_change_has_no_problems = api.build('technique', TECHNIQUE, s => {
  s.values.name = 'Read bitstream from a device';
  s.values.subtechniques = ['DFT-1044', 'DFT-1099'];
});

cases.technique_clear_details = api.build('technique', TECHNIQUE, s => {
  s.values.details = '';
});

cases.weakness_clear_description = api.build('weakness', { ...WEAKNESS, description: 'Some description' }, s => {
  s.values.description = '';
});

const labels = {};
for (const [type, spec] of Object.entries(api.EDIT_SPECS)) {
  labels[type] = { idLabel: spec.idLabel, issueLabels: spec.issueLabels, fields: spec.fields.map(f => f.label) };
}

// The fixtures are echoed so test_editor_body.py can check its own copies
// match, rather than trusting two hand-maintained versions to stay equal.
process.stdout.write(JSON.stringify({ cases, labels, fixtures: { TECHNIQUE, WEAKNESS, MITIGATION } }, null, 1));
