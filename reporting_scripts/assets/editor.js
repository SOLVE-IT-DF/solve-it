/* ── Suggest-an-edit form ───────────────────────────────────────────────
   Loaded verbatim by generate_html_from_kb.py and inlined into the page, so
   braces here are ordinary JavaScript and are not f-string escaped.

   Why this exists: the edit links used to point at a GitHub issue form with
   every field prefilled from the URL. GitHub now resists edits made to those
   prefilled fields, so a contributor cannot change what the link put there.
   Editing therefore happens here instead, and GitHub receives a finished
   issue body rather than a form to be filled in.

   The body is written in the shape the issue form itself produces —
   `### <label>` headings, with a fenced block for the fields the form renders
   as `text`. admin/issue_parsers/ reads that shape, and the Actions that act
   on it key off the issue's labels rather than the template, so an issue
   built here goes through the existing pipeline unchanged.

   Only fields the contributor actually changed are sent. A blank field means
   "leave this alone", so unchanged fields are simply absent, which keeps the
   proposal from reverting anyone else's edits made in the meantime and keeps
   the URL short. A list the contributor deliberately emptied is sent as the
   `_none_` sentinel, which the parsers read as "replace with an empty list". */

const EDITOR_REPO_URL = (typeof REPO_URL !== 'undefined')
  ? REPO_URL
  : 'https://github.com/SOLVE-IT-DF/solve-it';

/* GitHub rejects very long request URIs. The limit is not published exactly,
   so this sits well below where failures start being reported. */
const EDITOR_MAX_URL = 8000;

/* Understood by is_clear_request() in admin/issue_parsers/update_utils.py. */
const EDITOR_CLEAR = '_none_';

const EDITOR_RELEVANCE_MAX = 280;

const ASTM_CLASSES = [
  ['ASTM_INCOMP',   'Incompleteness'],
  ['ASTM_INAC_EX',  'Inaccuracy: Existence'],
  ['ASTM_INAC_AS',  'Inaccuracy: Association'],
  ['ASTM_INAC_ALT', 'Inaccuracy: Alteration'],
  ['ASTM_INAC_COR', 'Inaccuracy: Corruption'],
  ['ASTM_MISINT',   'Misinterpretation'],
];

/* The three item types, declared once. The form is built from this, and so is
   the issue body — so a label cannot drift between what is shown and what is
   sent. Every `label` must match a field label in the matching issue template,
   because that is what the parsers look the value up by; a test asserts it.

   `issueLabels` deliberately differs from the matching template's own labels.
   The content label is the same, because autoimplement-update-item.yml and
   validate-revised-proposal.yml are gated on it. `form input` is not included:
   this is a blank issue, not a form submission, and nothing reads that label
   on an issue from here — issue-preview.yml tests it against the opened-issue
   event payload, which cannot contain a label added after the issue opened.
   `explorer` is included in its place, so the route an issue took is visible
   in the issue list beside the existing `trwm`. Nothing is gated on it.

   These labels only take effect for a contributor who may label issues;
   GitHub ignores the `labels=` parameter for everyone else, which is why
   .github/workflows/issue-preview.yml applies the same set from the marker. */
const EDIT_SPECS = {
  technique: {
    noun: 'technique',
    idLabel: 'Technique ID',
    issueLabels: ['content: update technique', 'explorer'],
    titlePrefix: 'Update technique',
    fields: [
      {key: 'name', label: 'New technique name', kind: 'text',
       help: 'Sentence case, starting with an imperative verb — for example "Connect", "Locate", "Use".'},
      {key: 'description', label: 'New description', kind: 'prose', render: 'text',
       help: 'You can cite references inline using [DFCite-xxxx].'},
      {key: 'details', label: 'New details', kind: 'prose', render: 'text', rows: 8,
       help: 'The longer write-up. You can cite references inline using [DFCite-xxxx].'},
      {key: 'synonyms', label: 'Synonyms', kind: 'lines', render: 'text',
       help: 'One per line.'},
      {key: 'examples', label: 'Examples', kind: 'lines', render: 'text',
       help: 'Tools or implementations, one per line.'},
      {key: 'subtechniques', label: 'Subtechnique IDs', kind: 'ids', render: 'text', source: 'techniques',
       help: 'Start typing a technique ID or name.'},
      {key: 'weaknesses', label: 'Weakness IDs', kind: 'ids', render: 'text', source: 'weaknesses',
       help: 'Start typing a weakness ID or description. Similar weaknesses already in the knowledge base are offered first.'},
      {key: 'CASE_input_classes', label: 'Ontology input classes', kind: 'terms', render: 'text',
       help: 'Classes and properties from the CASE, UCO and SOLVE-IT ontologies. Type free text and press Enter to propose one that does not exist yet.'},
      {key: 'CASE_output_classes', label: 'Ontology output classes', kind: 'terms', render: 'text',
       help: 'Classes and properties from the CASE, UCO and SOLVE-IT ontologies. Type free text and press Enter to propose one that does not exist yet.'},
      {key: 'references', label: 'References', kind: 'refs', render: 'text',
       help: 'Existing DFCite IDs. To add a reference that is not yet in the knowledge base, propose it first using the new reference form.'},
      {key: '_new_weaknesses', label: 'Propose new weaknesses', kind: 'additional', render: 'text',
       help: 'Weaknesses that do not exist yet, one per line. These are created as new entries and linked to this technique.'},
    ],
  },
  weakness: {
    noun: 'weakness',
    idLabel: 'Weakness ID',
    issueLabels: ['content: update weakness', 'explorer'],
    titlePrefix: 'Update weakness',
    fields: [
      {key: 'name', label: 'New weakness name', kind: 'text',
       help: 'The weakness itself — what can go wrong, stated as a sentence.'},
      {key: 'description', label: 'New description', kind: 'prose', render: 'text',
       help: 'Additional description, if any.'},
      {key: 'categories', label: 'Categories', kind: 'astm',
       help: 'The ASTM error classes this weakness falls under.'},
      {key: 'mitigations', label: 'Mitigation IDs', kind: 'ids', render: 'text', source: 'mitigations',
       help: 'Start typing a mitigation ID or description.'},
      {key: 'references', label: 'References', kind: 'refs', render: 'text',
       help: 'Existing DFCite IDs.'},
      {key: '_new_mitigations', label: 'Propose new mitigations', kind: 'additional', render: 'text',
       help: 'Mitigations that do not exist yet, one per line. These are created as new entries and linked to this weakness.'},
    ],
  },
  mitigation: {
    noun: 'mitigation',
    idLabel: 'Mitigation ID',
    issueLabels: ['content: update mitigation', 'explorer'],
    titlePrefix: 'Update mitigation',
    fields: [
      {key: 'name', label: 'New mitigation name', kind: 'text',
       help: 'The mitigation itself — what to do, stated as a sentence.'},
      {key: 'description', label: 'New description', kind: 'prose', render: 'text',
       help: 'Additional description, if any.'},
      // `label` here is the heading shown in the form. This field is the one
      // case where that is not also an issue heading: it emits the template's
      // dropdown and ID fields instead, named in `emits`.
      {key: 'technique', label: 'Linked technique', kind: 'link',
       emits: ['Linked technique action', 'Linked technique ID'],
       help: 'Some mitigations are themselves a technique in the knowledge base. DFM-1007 is an example.'},
      {key: 'references', label: 'References', kind: 'refs', render: 'text',
       help: 'Existing DFCite IDs.'},
    ],
  },
};

/* Populated by generate_html_from_kb.py from reporting_scripts/assets/
   ontology_classes.json. Absent or empty means the ontology fields fall back
   to free text, which is still a usable form. */
const EDITOR_TERMS = (typeof ONTOLOGY_TERMS !== 'undefined' && Array.isArray(ONTOLOGY_TERMS))
  ? ONTOLOGY_TERMS
  : [];
const EDITOR_TERM_BY_URI = Object.fromEntries(EDITOR_TERMS.map(t => [t.uri, t]));

let editorState = null;

/* ── Value handling ─────────────────────────────────────────────────── */

/** The current knowledge base value for a field, normalised to the shape the
 *  editor holds it in. */
function editorReadValue(item, field) {
  switch (field.kind) {
    case 'text':
    case 'prose':
      return item[field.key] || '';
    case 'lines':
    case 'ids':
    case 'terms':
    case 'astm':
      return (item[field.key] || []).slice();
    case 'refs':
      return (item[field.key] || []).map(r => (r && typeof r === 'object')
        ? {id: r.DFCite_id || '', relevance: r.relevance_summary_280 || ''}
        : {id: String(r), relevance: ''});
    case 'link':
      return {action: 'keep', id: item.technique || ''};
    case 'additional':
      return '';
    default:
      return '';
  }
}

/** Comparable form of a value, so "changed" means changed in substance. */
function editorSerialise(value, field) {
  if (field.kind === 'refs') {
    return value.map(r => r.id + '|' + (r.relevance || '').trim()).join('\n');
  }
  if (field.kind === 'link') {
    return value.action + '|' + (value.action === 'set' ? value.id.trim() : '');
  }
  if (field.kind === 'astm') {
    // Checkbox order is the order boxes were ticked, not a change.
    return value.slice().sort().join('\n');
  }
  if (Array.isArray(value)) return value.map(v => String(v).trim()).filter(Boolean).join('\n');
  return String(value).trim();
}

function editorIsChanged(field) {
  if (field.kind === 'additional') return false;
  if (field.kind === 'link') return editorState.values[field.key].action !== 'keep';
  return editorSerialise(editorState.values[field.key], field)
      !== editorSerialise(editorState.original[field.key], field);
}

/* ── Issue body ─────────────────────────────────────────────────────── */

/** One `### label` section, fenced when the real form would render it as text.
 *  Fencing matters beyond fidelity: parse_issue_body() ignores headings found
 *  inside a fence, so a value containing a line like `### Notes` cannot be
 *  mistaken for the start of the next field. */
function editorSection(label, value, fence) {
  const body = fence
    ? '```text\n' + value + '\n```'
    : value;
  return '### ' + label + '\n\n' + body + '\n';
}

/** A value that would corrupt the body it is placed in. The parser toggles on
 *  any line starting with a fence, so a value containing one would silently
 *  swallow or split the fields around it. */
function editorFenceHazard(value) {
  return String(value).split('\n').some(line => line.trim().startsWith('```'));
}

/** The changed fields, as sections ready to be joined into an issue body. */
function editorChangedSections() {
  const spec = EDIT_SPECS[editorState.type];
  const sections = [];

  sections.push({label: spec.idLabel, value: editorState.item.id, fence: false});

  for (const field of spec.fields) {
    const value = editorState.values[field.key];
    const fence = field.render === 'text';

    if (field.kind === 'additional') {
      const text = String(value).trim();
      if (text) sections.push({label: field.label, value: text, fence});
      continue;
    }

    if (field.kind === 'link') {
      if (value.action === 'keep') continue;
      const [actionLabel, idLabel] = field.emits;
      if (value.action === 'remove') {
        sections.push({label: actionLabel, value: 'Remove current link', fence: false});
      } else {
        sections.push({label: actionLabel, value: 'Set new value (provide ID below)', fence: false});
        sections.push({label: idLabel, value: value.id.trim(), fence: false});
      }
      continue;
    }

    if (!editorIsChanged(field)) continue;

    if (field.kind === 'text' || field.kind === 'prose') {
      // A blank value would read as "leave alone" at the parser, so an
      // emptied field is sent as the sentinel instead. The name cannot be
      // emptied; editorProblems() refuses to submit that.
      const text = String(value).trim();
      sections.push({label: field.label, value: text || EDITOR_CLEAR, fence});
      continue;
    }

    if (field.kind === 'refs') {
      const lines = value
        .filter(r => r.id)
        .map(r => r.relevance.trim() ? r.id + ' | ' + r.relevance.trim() : r.id);
      sections.push({label: field.label, value: lines.length ? lines.join('\n') : EDITOR_CLEAR, fence});
      continue;
    }

    const lines = value.map(v => String(v).trim()).filter(Boolean);
    sections.push({label: field.label, value: lines.length ? lines.join('\n') : EDITOR_CLEAR, fence});
  }

  const notes = (editorState.notes || '').trim();
  if (notes) sections.push({label: 'Any other notes', value: notes, fence: false});

  return sections;
}

/* GitHub applies the `labels=` query parameter only for users who could add
   those labels by hand, and most contributors cannot. The template route used
   to apply them server-side; this route has no template. So the body also
   carries a marker that .github/workflows/issue-preview.yml reads to apply the
   labels itself. It sits before the first heading, where parse_issue_body()
   ignores it, and it is an HTML comment, so it does not show in the issue. */
function editorMarker() {
  return '<!-- solveit-explorer: update-' + editorState.type + ' -->';
}

function editorBuildBody(sections) {
  return editorMarker() + '\n\n' +
    sections.map(s => editorSection(s.label, s.value, s.fence)).join('\n');
}

function editorBuildUrl(sections) {
  const spec = EDIT_SPECS[editorState.type];
  const item = editorState.item;
  const name = editorState.values.name || item.name || '';
  const params = new URLSearchParams();
  params.set('title', spec.titlePrefix + ': ' + item.id + (name ? ': ' + name : ''));
  params.set('labels', spec.issueLabels.join(','));
  params.set('body', editorBuildBody(sections));
  return EDITOR_REPO_URL + '/issues/new?' + params.toString();
}

/* ── Lookup sources ─────────────────────────────────────────────────── */

function editorSourceItems(source) {
  if (source === 'techniques') return DB.techniques;
  if (source === 'weaknesses') return DB.weaknesses;
  if (source === 'mitigations') return DB.mitigations;
  return [];
}

function editorLookup(source, id) {
  if (source === 'techniques') return TMap[id];
  if (source === 'weaknesses') return WMap[id];
  if (source === 'mitigations') return MMap[id];
  return null;
}

/** Rank items against a query. An ID match wins, then a name that starts with
 *  the query, then how many of the query's words the name contains — which is
 *  what surfaces a weakness already in the knowledge base that says much the
 *  same thing as the one being typed. */
function editorRank(items, query, chosen, limit) {
  const q = query.trim().toLowerCase();
  if (!q) {
    return items.filter(it => !chosen.includes(it.id)).slice(0, limit)
      .map(it => ({item: it, score: 0}));
  }
  const words = q.split(/\s+/).filter(w => w.length > 2);
  const scored = [];
  for (const it of items) {
    if (chosen.includes(it.id)) continue;
    const id = (it.id || '').toLowerCase();
    const name = (it.name || '').toLowerCase();
    let score = 0;
    if (id === q) score = 1000;
    else if (id.includes(q)) score = 500;
    else if (name.startsWith(q)) score = 400;
    else if (name.includes(q)) score = 300;
    if (words.length) {
      const hits = words.filter(w => name.includes(w)).length;
      if (hits) score = Math.max(score, 100 + (hits / words.length) * 150);
    }
    if (score > 0) scored.push({item: it, score});
  }
  scored.sort((a, b) => b.score - a.score || a.item.id.localeCompare(b.item.id));
  return scored.slice(0, limit);
}

function editorRankTerms(query, chosen, limit) {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const scored = [];
  for (const term of EDITOR_TERMS) {
    if (chosen.includes(term.uri)) continue;
    const name = term.name.toLowerCase();
    let score = 0;
    if (name === q) score = 1000;
    else if (name.startsWith(q)) score = 500;
    else if (name.includes(q)) score = 300;
    else if (term.uri.toLowerCase().includes(q)) score = 200;
    else if ((term.description || '').toLowerCase().includes(q)) score = 80;
    if (score > 0) {
      if (term.kind === 'class') score += 25;
      scored.push({term, score});
    }
  }
  scored.sort((a, b) => b.score - a.score || a.term.name.localeCompare(b.term.name));
  return scored.slice(0, limit);
}

function editorCiteItems() {
  return Object.keys(CiteMap || {}).sort().map(id => ({id, name: citeText(id)}));
}

/* ── Validation ────────────────────────────────────────────────────── */
/** Reasons the proposal cannot be submitted as it stands, worst first. */
function editorProblems(sections, url) {
  const spec = EDIT_SPECS[editorState.type];
  const problems = [];

  for (const section of sections) {
    if (editorFenceHazard(section.value)) {
      problems.push('"' + section.label + '" contains a line starting with ``` , which the issue parser cannot read. Please remove it.');
    }
  }

  for (const field of spec.fields) {
    if (field.kind === 'refs') {
      for (const ref of editorState.values[field.key]) {
        if (ref.relevance.length > EDITOR_RELEVANCE_MAX) {
          problems.push('The relevance summary for ' + ref.id + ' is over ' + EDITOR_RELEVANCE_MAX + ' characters.');
        }
      }
    }
    if (field.kind === 'ids') {
      for (const id of editorState.values[field.key]) {
        if (!editorLookup(field.source, id)) {
          problems.push(id + ' in "' + field.label + '" is not in the knowledge base.');
        }
      }
    }
    if (field.kind === 'text' && field.key === 'name' && !String(editorState.values[field.key]).trim()) {
      problems.push('The name cannot be empty.');
    }
  }

  const link = editorState.values.technique;
  if (link && link.action === 'set' && !link.id) {
    problems.push('Choose the technique to link, or pick a different option.');
  }

  if (url.length > EDITOR_MAX_URL) {
    problems.push('The change is too long to send through a URL (' + Math.round(url.length / 1024) +
      ' KB). Use "Review changes" to copy the issue body, then paste it into a blank issue.');
  }

  return problems;
}

/* ── Form rendering ─────────────────────────────────────────────────── */

function editorEsc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function editorEl(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text != null) el.textContent = text;
  return el;
}

function editorEnsureOverlay() {
  let overlay = document.getElementById('editorOverlay');
  if (overlay) return overlay;

  overlay = editorEl('div', 'editor-overlay');
  overlay.id = 'editorOverlay';
  overlay.innerHTML =
    '<div class="editor-dialog" role="dialog" aria-modal="true" aria-labelledby="editorTitle">' +
      '<div class="editor-head">' +
        '<div class="editor-head-title" id="editorTitle">' +
          '<span id="editorHeadText"></span>' +
          '<span class="editor-head-id" id="editorHeadId"></span>' +
        '</div>' +
        '<button class="editor-close" id="editorCloseBtn" title="Close (Esc)" aria-label="Close">&#10005;</button>' +
      '</div>' +
      '<div class="editor-intro" id="editorIntro"></div>' +
      '<div class="editor-body" id="editorBody"></div>' +
      '<div class="editor-foot">' +
        '<div class="editor-status" id="editorStatus"></div>' +
        '<button class="editor-secondary" id="editorReviewBtn">Review changes</button>' +
        '<button class="editor-secondary" id="editorDoneBtn" style="display:none">Done</button>' +
        '<button class="editor-submit" id="editorSubmitBtn">Open GitHub issue</button>' +
      '</div>' +
    '</div>';
  document.body.appendChild(overlay);

  overlay.addEventListener('mousedown', e => { if (e.target === overlay) editorClose(); });
  document.getElementById('editorCloseBtn').addEventListener('click', editorClose);
  document.getElementById('editorReviewBtn').addEventListener('click', editorToggleReview);
  document.getElementById('editorDoneBtn').addEventListener('click', editorClose);
  document.getElementById('editorSubmitBtn').addEventListener('click', editorSubmit);
  return overlay;
}

function editorClose() {
  const overlay = document.getElementById('editorOverlay');
  if (overlay) overlay.classList.remove('open');
  editorState = null;
}

/** Open the edit form for an item. `focusKey` optionally names a field to
 *  scroll to, which is how the [edit] link beside a relevance summary opens the
 *  form already scrolled to the references rather than the top. */
function openEditor(type, id, focusKey) {
  const spec = EDIT_SPECS[type];
  if (!spec) return;
  const item = editorLookup(type === 'technique' ? 'techniques'
                          : type === 'weakness' ? 'weaknesses' : 'mitigations', id);
  if (!item) return;

  editorState = {type, item, values: {}, original: {}, notes: '', reviewing: false, submitted: false};
  for (const field of spec.fields) {
    editorState.original[field.key] = editorReadValue(item, field);
    editorState.values[field.key] = editorReadValue(item, field);
  }

  editorEnsureOverlay();
  document.getElementById('editorHeadText').textContent = 'Suggest an edit to this ' + spec.noun;
  document.getElementById('editorHeadId').textContent = item.id + (item.name ? ' — ' + item.name : '');
  document.getElementById('editorIntro').innerHTML =
    'Change what you want to change and leave the rest alone. Only the fields you edit are sent, ' +
    'so this proposal will not overwrite anyone else&rsquo;s changes to the other fields. ' +
    'Submitting opens a prepared GitHub issue that you can read through before posting.';

  editorRenderForm();
  document.getElementById('editorOverlay').classList.add('open');

  const target = focusKey
    ? document.querySelector('#editorBody .editor-field[data-key="' + focusKey + '"]')
    : null;
  if (target) {
    target.scrollIntoView({block: 'start'});
    const input = target.querySelector('input, textarea');
    if (input) input.focus();
  } else {
    const first = document.querySelector('#editorBody input, #editorBody textarea');
    if (first) first.focus();
  }
}

function editorRenderForm() {
  const spec = EDIT_SPECS[editorState.type];
  const body = document.getElementById('editorBody');
  body.innerHTML = '';
  editorState.reviewing = false;
  document.getElementById('editorReviewBtn').textContent = 'Review changes';

  for (const field of spec.fields) {
    const wrap = editorEl('div', 'editor-field');
    wrap.dataset.key = field.key;
    wrap.appendChild(editorEl('label', 'editor-field-label', field.label));
    if (field.help) wrap.appendChild(editorEl('div', 'editor-field-help', field.help));
    editorMountField(wrap, field);
    body.appendChild(wrap);
  }

  const notesWrap = editorEl('div', 'editor-field');
  notesWrap.appendChild(editorEl('label', 'editor-field-label', 'Any other notes'));
  notesWrap.appendChild(editorEl('div', 'editor-field-help',
    'Anything a reviewer should know — why the change is being proposed, or an ontology class that does not exist yet.'));
  const notes = editorEl('textarea', 'editor-textarea');
  notes.rows = 3;
  notes.value = editorState.notes;
  notes.addEventListener('input', () => { editorState.notes = notes.value; editorRefresh(); });
  notesWrap.appendChild(notes);
  body.appendChild(notesWrap);

  editorRefresh();
}

function editorMountField(wrap, field) {
  switch (field.kind) {
    case 'text':      return editorMountText(wrap, field);
    case 'prose':     return editorMountProse(wrap, field);
    case 'additional':return editorMountAdditional(wrap, field);
    case 'lines':     return editorMountLines(wrap, field);
    case 'ids':       return editorMountChips(wrap, field, 'ids');
    case 'terms':     return editorMountChips(wrap, field, 'terms');
    case 'astm':      return editorMountAstm(wrap, field);
    case 'refs':      return editorMountRefs(wrap, field);
    case 'link':      return editorMountLink(wrap, field);
  }
}

function editorMountText(wrap, field) {
  const input = editorEl('input', 'editor-input');
  input.type = 'text';
  input.value = editorState.values[field.key];
  input.addEventListener('input', () => {
    editorState.values[field.key] = input.value;
    editorRefresh();
  });
  wrap.appendChild(input);
}

function editorMountProse(wrap, field) {
  const area = editorEl('textarea', 'editor-textarea');
  area.rows = field.rows || 4;
  area.value = editorState.values[field.key];
  area.addEventListener('input', () => {
    editorState.values[field.key] = area.value;
    editorRefresh();
  });
  wrap.appendChild(area);
}

function editorMountAdditional(wrap, field) {
  const area = editorEl('textarea', 'editor-textarea');
  area.rows = 3;
  area.value = editorState.values[field.key] || '';
  area.placeholder = 'One per line. Leave blank if you are not proposing any.';
  area.addEventListener('input', () => {
    editorState.values[field.key] = area.value;
    editorRefresh();
  });
  wrap.appendChild(area);
}

function editorMountLines(wrap, field) {
  const area = editorEl('textarea', 'editor-textarea');
  area.rows = 3;
  area.value = editorState.values[field.key].join('\n');
  area.placeholder = 'One per line. Empty this box to remove them all.';
  area.addEventListener('input', () => {
    editorState.values[field.key] = area.value.split('\n');
    editorRefresh();
  });
  wrap.appendChild(area);
}

function editorMountAstm(wrap, field) {
  const box = editorEl('div', 'editor-checks');
  for (const [code, name] of ASTM_CLASSES) {
    const label = editorEl('label', 'editor-check');
    const cb = editorEl('input');
    cb.type = 'checkbox';
    cb.checked = editorState.values[field.key].includes(code);
    cb.addEventListener('change', () => {
      const chosen = editorState.values[field.key];
      if (cb.checked) {
        if (!chosen.includes(code)) chosen.push(code);
      } else {
        editorState.values[field.key] = chosen.filter(c => c !== code);
      }
      editorRefresh();
    });
    label.appendChild(cb);
    const text = editorEl('span');
    text.innerHTML = '<code>' + editorEsc(code) + '</code> &mdash; ' + editorEsc(name);
    label.appendChild(text);
    box.appendChild(label);
  }
  wrap.appendChild(box);
}

/* ── Chip lists with autocomplete ───────────────────────────────────── */

/** `mode` is 'ids' (knowledge base items, picked from the list only) or
 *  'terms' (ontology IRIs, where free text is allowed because a contributor
 *  may need a class that has not been catalogued yet). */
function editorMountChips(wrap, field, mode) {
  const outer = editorEl('div', 'editor-suggest-wrap');
  const box = editorEl('div', 'editor-chips');
  const input = editorEl('input', 'editor-chip-input');
  input.type = 'text';
  input.placeholder = mode === 'ids' ? 'Search by ID or text…' : 'Search classes and properties…';
  const suggest = editorEl('div', 'editor-suggest');
  let active = -1;

  function values() { return editorState.values[field.key]; }

  function redrawChips() {
    box.querySelectorAll('.editor-chip').forEach(c => c.remove());
    values().forEach((value, i) => {
      const chip = editorEl('span', 'editor-chip');
      let label = '';
      if (mode === 'ids') {
        const item = editorLookup(field.source, value);
        chip.appendChild(editorEl('span', 'editor-chip-id', value));
        label = item ? (item.name || '') : 'not found in the knowledge base';
        if (!item) chip.classList.add('unknown');
      } else {
        const term = EDITOR_TERM_BY_URI[value];
        chip.appendChild(editorEl('span', 'editor-chip-id', term ? term.name : '?'));
        label = term ? '' : value;
        if (!term) chip.classList.add('unknown');
      }
      if (label) {
        const text = editorEl('span', 'editor-chip-text', label);
        text.title = label;
        chip.appendChild(text);
      }
      chip.title = value;
      const remove = editorEl('button', 'editor-chip-remove', '×');
      remove.type = 'button';
      remove.setAttribute('aria-label', 'Remove ' + value);
      remove.addEventListener('click', () => {
        editorState.values[field.key] = values().filter((_, j) => j !== i);
        redrawChips();
        editorRefresh();
      });
      chip.appendChild(remove);
      box.insertBefore(chip, input);
    });
  }

  function closeSuggest() { suggest.classList.remove('open'); active = -1; }

  function add(value) {
    const trimmed = String(value).trim();
    if (!trimmed || values().includes(trimmed)) { input.value = ''; closeSuggest(); return; }
    // A single-value field (a mitigation's one linked technique) replaces
    // rather than accumulates.
    if (field.single) editorState.values[field.key] = [trimmed];
    else values().push(trimmed);
    input.value = '';
    closeSuggest();
    redrawChips();
    editorRefresh();
  }

  function renderSuggest() {
    const query = input.value;
    suggest.innerHTML = '';
    let rows = [];

    if (mode === 'ids') {
      rows = editorRank(editorSourceItems(field.source), query, values(), 8).map(r => ({
        value: r.item.id,
        id: r.item.id,
        name: r.item.name || '',
        meta: '',
        tags: [],
      }));
    } else {
      // Source and kind are separate things a contributor needs: which
      // ontology a term comes from, and whether it is a class or a property.
      rows = editorRankTerms(query, values(), 10).map(r => ({
        value: r.term.uri,
        id: r.term.name,
        name: '',
        meta: r.term.description || r.term.uri,
        tags: [r.term.source, r.term.kind],
      }));
    }

    if (!rows.length) {
      if (!query.trim()) { closeSuggest(); return; }
      const empty = editorEl('div', 'editor-suggest-empty',
        mode === 'terms'
          ? 'No match. Press Enter to propose "' + query.trim() + '" as a new class — describe it in the notes below.'
          : 'No match.');
      suggest.appendChild(empty);
      suggest.classList.add('open');
      return;
    }

    rows.forEach((row, i) => {
      const el = editorEl('div', 'editor-suggest-item');
      el.dataset.index = String(i);
      let html = '';
      // Rendered right to left, because each tag floats right.
      for (const tag of (row.tags || []).slice().reverse()) {
        html += '<span class="editor-suggest-tag' + (tag === 'SOLVE-IT' ? ' src-solveit' : '') + '">' +
                editorEsc(tag) + '</span>';
      }
      html += '<span class="editor-suggest-id">' + editorEsc(row.id) + '</span>';
      if (row.name) html += '<span class="editor-suggest-name">' + editorEsc(row.name) + '</span>';
      if (row.meta) html += '<span class="editor-suggest-meta">' + editorEsc(row.meta) + '</span>';
      el.innerHTML = html;
      el.addEventListener('mousedown', e => { e.preventDefault(); add(row.value); });
      suggest.appendChild(el);
    });
    suggest.classList.add('open');
    active = -1;
  }

  function highlight(delta) {
    const items = suggest.querySelectorAll('.editor-suggest-item');
    if (!items.length) return;
    if (active >= 0) items[active].classList.remove('active');
    active = (active + delta + items.length) % items.length;
    items[active].classList.add('active');
    items[active].scrollIntoView({block: 'nearest'});
  }

  input.addEventListener('input', renderSuggest);
  input.addEventListener('focus', renderSuggest);
  input.addEventListener('blur', () => setTimeout(closeSuggest, 120));
  input.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); highlight(1); return; }
    if (e.key === 'ArrowUp') { e.preventDefault(); highlight(-1); return; }
    if (e.key === 'Escape') {
      // Close the list only; stop here so the page's own Escape handler
      // does not also close the item panel behind the dialog.
      e.stopPropagation();
      closeSuggest();
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      const items = suggest.querySelectorAll('.editor-suggest-item');
      if (active >= 0 && items[active]) {
        items[active].dispatchEvent(new MouseEvent('mousedown'));
      } else if (mode === 'terms' && input.value.trim()) {
        add(input.value);
      }
      return;
    }
    if (e.key === 'Backspace' && !input.value && values().length) {
      editorState.values[field.key] = values().slice(0, -1);
      redrawChips();
      editorRefresh();
    }
  });

  box.addEventListener('click', () => input.focus());
  box.appendChild(input);
  outer.appendChild(box);
  outer.appendChild(suggest);
  wrap.appendChild(outer);
  redrawChips();
}

/* ── References ─────────────────────────────────────────────────────── */

function editorMountRefs(wrap, field) {
  const list = editorEl('div');
  const adder = editorEl('div', 'editor-suggest-wrap');
  const addBox = editorEl('div', 'editor-chips');
  const input = editorEl('input', 'editor-chip-input');
  input.type = 'text';
  input.placeholder = 'Add an existing DFCite ID…';
  const suggest = editorEl('div', 'editor-suggest');
  let active = -1;

  function values() { return editorState.values[field.key]; }

  function redraw() {
    list.innerHTML = '';
    values().forEach((ref, i) => {
      const row = editorEl('div', 'editor-ref');
      const top = editorEl('div', 'editor-ref-top');
      top.appendChild(editorEl('span', 'editor-ref-id', ref.id));
      const cite = editorEl('span', 'editor-ref-cite', citeText(ref.id));
      cite.title = citeText(ref.id);
      top.appendChild(cite);
      const remove = editorEl('button', 'editor-chip-remove', '×');
      remove.type = 'button';
      remove.setAttribute('aria-label', 'Remove ' + ref.id);
      remove.addEventListener('click', () => {
        editorState.values[field.key] = values().filter((_, j) => j !== i);
        redraw();
        editorRefresh();
      });
      top.appendChild(remove);
      row.appendChild(top);

      const relevance = editorEl('input', 'editor-input editor-ref-relevance');
      relevance.type = 'text';
      relevance.value = ref.relevance;
      relevance.placeholder = 'Why this reference matters to this item specifically';
      const count = editorEl('div', 'editor-ref-count');
      function updateCount() {
        count.textContent = relevance.value.length + ' / ' + EDITOR_RELEVANCE_MAX;
        count.classList.toggle('over', relevance.value.length > EDITOR_RELEVANCE_MAX);
      }
      relevance.addEventListener('input', () => {
        ref.relevance = relevance.value;
        updateCount();
        editorRefresh();
      });
      updateCount();
      row.appendChild(relevance);
      row.appendChild(count);
      list.appendChild(row);
    });
  }

  function closeSuggest() { suggest.classList.remove('open'); active = -1; }

  function add(id) {
    if (!id || values().some(r => r.id === id)) { input.value = ''; closeSuggest(); return; }
    values().push({id, relevance: ''});
    input.value = '';
    closeSuggest();
    redraw();
    editorRefresh();
  }

  function renderSuggest() {
    suggest.innerHTML = '';
    const chosen = values().map(r => r.id);
    const rows = editorRank(editorCiteItems(), input.value, chosen, 8);
    if (!rows.length) { closeSuggest(); return; }
    rows.forEach((r, i) => {
      const el = editorEl('div', 'editor-suggest-item');
      el.dataset.index = String(i);
      el.innerHTML = '<span class="editor-suggest-id">' + editorEsc(r.item.id) + '</span>' +
                     '<span class="editor-suggest-meta">' + editorEsc(r.item.name) + '</span>';
      el.addEventListener('mousedown', e => { e.preventDefault(); add(r.item.id); });
      suggest.appendChild(el);
    });
    suggest.classList.add('open');
    active = -1;
  }

  input.addEventListener('input', renderSuggest);
  input.addEventListener('focus', renderSuggest);
  input.addEventListener('blur', () => setTimeout(closeSuggest, 120));
  input.addEventListener('keydown', e => {
    const items = suggest.querySelectorAll('.editor-suggest-item');
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!items.length) return;
      if (active >= 0) items[active].classList.remove('active');
      active = (active + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      items[active].classList.add('active');
      return;
    }
    if (e.key === 'Escape') { e.stopPropagation(); closeSuggest(); return; }
    if (e.key === 'Enter') {
      e.preventDefault();
      if (active >= 0 && items[active]) items[active].dispatchEvent(new MouseEvent('mousedown'));
      else if (/^DFCite-\d+$/.test(input.value.trim())) add(input.value.trim());
    }
  });

  addBox.addEventListener('click', () => input.focus());
  addBox.appendChild(input);
  adder.appendChild(addBox);
  adder.appendChild(suggest);

  const note = editorEl('div', 'editor-field-help');
  note.innerHTML = 'Not in the list? <a href="' + EDITOR_REPO_URL +
    '/issues/new?template=1d_propose-new-reference-form.yml" target="_blank" rel="noopener">Propose the reference first</a>, then add its DFCite ID here.';

  wrap.appendChild(list);
  wrap.appendChild(adder);
  wrap.appendChild(note);
  redraw();
}

/* ── Linked technique (mitigations) ─────────────────────────────────── */

function editorMountLink(wrap, field) {
  const value = editorState.values[field.key];
  const current = editorState.item.technique || '';
  const box = editorEl('div', 'editor-radios');
  const idWrap = editorEl('div');

  const options = [
    ['keep', current ? 'Leave it as ' + current : 'No linked technique — leave it that way'],
    ['set', current ? 'Link a different technique' : 'Link a technique'],
    ['remove', 'Remove the current link'],
  ];

  for (const [key, text] of options) {
    if (key === 'remove' && !current) continue;
    const label = editorEl('label', 'editor-radio');
    const radio = editorEl('input');
    radio.type = 'radio';
    radio.name = 'editor-link-action';
    radio.checked = value.action === key;
    radio.addEventListener('change', () => {
      value.action = key;
      idWrap.style.display = key === 'set' ? '' : 'none';
      editorRefresh();
    });
    label.appendChild(radio);
    label.appendChild(editorEl('span', null, text));
    box.appendChild(label);
  }

  const idField = {key: '_link_id', label: 'Linked technique ID', kind: 'ids', source: 'techniques', single: true};
  editorState.values._link_id = value.id ? [value.id] : [];
  editorMountChips(idWrap, idField, 'ids');
  idWrap.style.display = value.action === 'set' ? '' : 'none';

  // The chip list holds the value; editorRefresh() copies the last entry back
  // onto the link, because a mitigation links to at most one technique.

  wrap.appendChild(box);
  wrap.appendChild(idWrap);
}

/* ── Status and submission ──────────────────────────────────────────── */


function editorRefresh() {
  if (!editorState) return;
  editorSetSubmitted(false);

  // The linked technique is edited through a single-value chip list.
  const link = editorState.values.technique;
  if (link && typeof link === 'object' && Array.isArray(editorState.values._link_id)) {
    link.id = editorState.values._link_id[0] || '';
  }

  const spec = EDIT_SPECS[editorState.type];
  for (const field of spec.fields) {
    const wrap = document.querySelector('#editorBody .editor-field[data-key="' + field.key + '"]');
    if (wrap) wrap.classList.toggle('changed', editorIsChanged(field));
  }

  const sections = editorChangedSections();
  const url = editorBuildUrl(sections);
  // The ID section is always present, so it does not count as a change.
  const changeCount = sections.length - 1;
  const problems = editorProblems(sections, url);

  const status = document.getElementById('editorStatus');
  const submit = document.getElementById('editorSubmitBtn');

  if (problems.length) {
    status.textContent = problems[0] + (problems.length > 1 ? ' (and ' + (problems.length - 1) + ' more)' : '');
    status.classList.add('warn');
    submit.disabled = true;
  } else if (changeCount === 0) {
    status.textContent = 'No changes yet.';
    status.classList.remove('warn');
    submit.disabled = true;
  } else {
    status.textContent = changeCount + (changeCount === 1 ? ' field' : ' fields') + ' will be sent.';
    status.classList.remove('warn');
    submit.disabled = false;
  }

  if (editorState.reviewing) editorRenderReview();
}

function editorToggleReview() {
  if (!editorState) return;
  if (editorState.reviewing) { editorRenderForm(); return; }
  editorState.reviewing = true;
  document.getElementById('editorReviewBtn').textContent = 'Back to editing';
  editorRenderReview();
}

function editorRenderReview() {
  const body = document.getElementById('editorBody');
  const sections = editorChangedSections();
  body.innerHTML = '';

  const wrap = editorEl('div', 'editor-review');
  wrap.appendChild(editorEl('h4', null, 'This is what will be posted to GitHub'));

  if (sections.length <= 1) {
    wrap.appendChild(editorEl('div', 'editor-review-empty', 'Nothing has been changed yet.'));
  } else {
    wrap.appendChild(editorEl('pre', 'editor-review-diff', editorBuildBody(sections)));
    const copy = editorEl('button', 'editor-secondary', 'Copy issue body');
    copy.style.marginTop = '10px';
    copy.addEventListener('click', () => {
      navigator.clipboard.writeText(editorBuildBody(sections)).then(() => {
        copy.textContent = 'Copied';
        setTimeout(() => { copy.textContent = 'Copy issue body'; }, 1500);
      });
    });
    wrap.appendChild(copy);
  }
  body.appendChild(wrap);
}

/* The GitHub tab is where the issue is actually posted, so the form stays
   open with the edits in it until the contributor says they are done — if
   that tab fails to load, this is the only copy. What changes is the footer,
   which says so rather than looking like nothing happened. */
function editorSetSubmitted(submitted) {
  editorState.submitted = submitted;
  const status = document.getElementById('editorStatus');
  const submit = document.getElementById('editorSubmitBtn');
  const done = document.getElementById('editorDoneBtn');
  if (!status || !submit || !done) return;
  done.style.display = submitted ? '' : 'none';
  submit.textContent = submitted ? 'Open again' : 'Open GitHub issue';
  if (submitted) {
    status.textContent = 'Opened in a new tab. Once you have posted the issue there, press Done. ' +
      'If the tab did not open, use "Review changes" to copy the issue body.';
    status.classList.remove('warn');
  }
}

function editorSubmit() {
  if (!editorState) return;
  const sections = editorChangedSections();
  const url = editorBuildUrl(sections);
  if (editorProblems(sections, url).length) return;
  window.open(url, '_blank', 'noopener');
  editorSetSubmitted(true);
}

/* Keys that must not reach the page while the dialog is open. Escape closes
   an open suggestion list first and the dialog second, and in neither case may
   it reach the page's own Escape handler, which would close the item panel
   underneath the dialog. Tab cycles within the dialog, so keyboard focus
   cannot wander onto the page behind it. */
document.addEventListener('keydown', e => {
  if (!editorState) return;
  if (e.key === 'Escape') {
    // An open suggestion list is closed by its own input's handler, which
    // also stops the event there. Stopping it here instead would keep it
    // from ever reaching that input.
    if (document.querySelector('.editor-suggest.open')) return;
    e.stopPropagation();
    editorClose();
    return;
  }
  if (e.key === 'Tab') {
    const dialog = document.querySelector('#editorOverlay .editor-dialog');
    if (!dialog) return;
    const focusable = Array.from(dialog.querySelectorAll(
      'button:not(:disabled), input:not([type=hidden]), textarea, a[href], [tabindex]:not([tabindex="-1"])'
    )).filter(el => el.offsetParent !== null);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    } else if (!dialog.contains(document.activeElement)) {
      e.preventDefault(); first.focus();
    }
  }
}, true);

/* The page navigates between items by changing the hash — the browser's back
   button, a deep link, a click on a related weakness. The form belongs to the
   item that was open when it was raised, so leaving it up over a different item
   would invite editing one item in another one's form. */
window.addEventListener('hashchange', () => { if (editorState) editorClose(); });
