import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { planRepository, managedBlock, findBlock, applyPlan, rollback, readText, clientPlan, readRepository, hash, INPUTS, POLICY, CONFIG } from './install.mjs';

const policy = '# Comprehensive project memory\nTest policy with nine required views.\n';
const repository = 'BAS-More/test-fixture';
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'project-memory-test-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}
const filesAt = root => Object.fromEntries(INPUTS.map(file => [file, readText(root, file)]));
const makePlan = root => planRepository({ repository, files: filesAt(root), policy });

test('preserves all existing instructions, frontmatter, overrides and hook bytes; rerun is a no-op', t => {
  const root = fixture(t);
  fs.mkdirSync(path.join(root, '.husky'));
  fs.mkdirSync(path.join(root, '.claude'));
  const old = {
    'AGENTS.md': '\uFEFF---\r\nname: original\r\n---\r\nRead HANDOVER first.\r\n',
    'AGENTS.override.md': 'Override has mandatory rules.\n',
    'CLAUDE.md': 'Character layer LOCKED.\n@model-rules.md\n',
    '.claude/CLAUDE.md': 'Nested client instructions.\n',
    '.husky/pre-commit': '#!/bin/sh\nnpm run existing-check\n'
  };
  for (const [file, content] of Object.entries(old)) fs.writeFileSync(path.join(root, file), content);
  const plan = makePlan(root);
  const result = applyPlan(root, plan, path.join(root, 'backups'));
  assert.equal(result.applied, 6);
  for (const [file, content] of Object.entries(old)) {
    const after = fs.readFileSync(path.join(root, file), 'utf8');
    if (file.includes('pre-commit')) assert.equal(after, content);
    else assert.equal(after.replace(/<!-- bas-more-project-memory:v2:start -->[\s\S]*?<!-- bas-more-project-memory:v2:end -->\r?\n\r?\n/, ''), content);
  }
  assert.ok(fs.readFileSync(path.join(root, 'AGENTS.md'), 'utf8').startsWith('\uFEFF---\r\nname: original\r\n---\r\n'));
  assert.equal(makePlan(root).changes.length, 0);
  assert.equal(JSON.parse(readText(root, CONFIG)).graphReadiness, 'requires-repository-validation');
  rollback(result.journalPath);
  for (const [file, content] of Object.entries(old)) assert.equal(fs.readFileSync(path.join(root, file), 'utf8'), content);
  assert.equal(fs.existsSync(path.join(root, POLICY)), false);
});

test('controlled interruption restores installer changes and retains a recovery journal', t => {
  const root = fixture(t);
  fs.writeFileSync(path.join(root, 'AGENTS.md'), 'Original\n');
  let writes = 0;
  assert.throws(() => applyPlan(root, makePlan(root), path.join(root, 'backups'), {
    afterWrite: () => { if (++writes === 2) throw new Error('simulated interruption'); }
  }), /simulated interruption/);
  assert.equal(readText(root, 'AGENTS.md'), 'Original\n');
  assert.equal(readText(root, POLICY), null);
  assert.equal(readText(root, CONFIG), null);
  const journal = JSON.parse(fs.readFileSync(path.join(root, 'backups', fs.readdirSync(path.join(root, 'backups'))[0]), 'utf8'));
  assert.equal(journal.state, 'rolled-back');
});

test('rejects changed files at installation and preserves edits made after installation during rollback', t => {
  const root = fixture(t);
  fs.writeFileSync(path.join(root, 'AGENTS.md'), 'Original\n');
  const plan = makePlan(root);
  fs.appendFileSync(path.join(root, 'AGENTS.md'), 'Concurrent\n');
  assert.throws(() => applyPlan(root, plan, path.join(root, 'backups')), /Concurrent edit/);
  assert.equal(readText(root, POLICY), null);
  const result = applyPlan(root, makePlan(root), path.join(root, 'backups'));
  fs.appendFileSync(path.join(root, 'AGENTS.md'), 'Later edit\n');
  assert.throws(() => rollback(result.journalPath), /preserves a concurrent edit/);
  assert.ok(readText(root, 'AGENTS.md').endsWith('Later edit\n'));
});

test('does not replace manually edited policies, malformed markers or another repository identity', t => {
  const root = fixture(t);
  applyPlan(root, makePlan(root), path.join(root, 'backups'));
  fs.appendFileSync(path.join(root, POLICY), 'Human addition\n');
  assert.throws(() => makePlan(root), /edited/);
  assert.throws(() => managedBlock('<!-- bas-more-project-memory:v1:start -->', 'new'), /Malformed/);
  assert.throws(() => planRepository({ repository: 'BAS-More/another', files: filesAt(root), policy }), /identity/);
});

test('honors deferred and declined choices and the protected home-backup exclusion', () => {
  for (const choice of ['declined', 'deferred']) {
    const result = planRepository({ repository, files: { [CONFIG]: JSON.stringify({ choice }) }, policy });
    assert.equal(result.changes.length, 0);
  }
  assert.equal(planRepository({ repository: 'BAS-More/claude-home-backup', files: {}, policy }).outcome, 'excluded-protected-backup');
});

test('rejects path traversal and symbolic-link directories', t => {
  const root = fixture(t);
  assert.throws(() => readText(root, '../outside'), /Invalid/);
  const outside = fixture(t);
  fs.symlinkSync(outside, path.join(root, '.project-memory'), process.platform === 'win32' ? 'junction' : 'dir');
  assert.throws(() => makePlan(root), /symbolic link/);
});

test('writes the active Codex override and Claude rules without modifying inactive files or locked text', t => {
  const profile = fixture(t);
  fs.mkdirSync(path.join(profile, '.codex'));
  fs.mkdirSync(path.join(profile, '.claude'));
  fs.writeFileSync(path.join(profile, '.codex', 'AGENTS.md'), 'Inactive base\n');
  fs.writeFileSync(path.join(profile, '.codex', 'AGENTS.override.md'), 'Active contract\n');
  fs.writeFileSync(path.join(profile, '.claude', 'CLAUDE.md'), 'Character LOCKED\n');
  const plans = clientPlan(profile);
  assert.equal(plans[1].changes[0].file, 'AGENTS.override.md');
  for (const plan of plans) applyPlan(plan.root, plan, path.join(profile, 'backups'));
  assert.equal(fs.readFileSync(path.join(profile, '.codex', 'AGENTS.md'), 'utf8'), 'Inactive base\n');
  assert.ok(fs.readFileSync(path.join(profile, '.codex', 'AGENTS.override.md'), 'utf8').startsWith('Active contract\n'));
  assert.ok(fs.readFileSync(path.join(profile, '.claude', 'CLAUDE.md'), 'utf8').startsWith('Character LOCKED\n'));
  assert.ok(clientPlan(profile).every(plan => plan.changes.length === 0));
});

test('two repositories stay isolated and empty repositories receive truthful setup status', t => {
  const first = fixture(t), second = fixture(t);
  applyPlan(first, makePlan(first), path.join(first, 'backups'));
  assert.equal(readText(second, POLICY), null);
  assert.equal(JSON.parse(readText(first, CONFIG)).repository, repository);
  assert.equal(JSON.parse(readText(first, CONFIG)).requiredViews.length, 9);
  assert.notEqual(JSON.parse(readText(first, CONFIG)).graphReadiness, 'complete');
});

test('preserves Git instruction aliases on Windows-style checkouts and rejects escaping link targets', t => {
  const root = fixture(t);
  const git = (args, options = {}) => execFileSync('git', args, { cwd: root, encoding: 'utf8', ...options });
  git(['init', '-q']);
  git(['config', 'core.symlinks', 'false']);
  fs.writeFileSync(path.join(root, 'AGENTS.md'), 'Shared original rules\n');
  fs.writeFileSync(path.join(root, 'CLAUDE.md'), 'AGENTS.md');
  const blob = git(['hash-object', '-w', '--stdin'], { input: 'AGENTS.md' }).trim();
  git(['update-index', '--add', '--cacheinfo', '120000,' + blob + ',CLAUDE.md']);
  const beforeIndex = git(['ls-files', '--stage']);
  const data = readRepository(root);
  assert.deepEqual(data.aliases, { 'CLAUDE.md': 'AGENTS.md' });
  const plan = planRepository({ repository, policy, ...data });
  assert.ok(plan.changes.every(change => change.file !== 'CLAUDE.md'));
  applyPlan(root, plan, path.join(root, 'backups'));
  assert.equal(fs.readFileSync(path.join(root, 'CLAUDE.md'), 'utf8'), 'AGENTS.md');
  assert.equal(git(['ls-files', '--stage']), beforeIndex);
  assert.equal(planRepository({ repository, policy, ...readRepository(root) }).changes.length, 0);
  fs.writeFileSync(path.join(root, 'CLAUDE.md'), '../outside');
  assert.throws(() => readRepository(root), /Unsupported instruction alias/);
});

function formattedFixture(root) {
  applyPlan(root, makePlan(root), path.join(root, 'backups'));
  const digest = value => createHash('sha256').update(value).digest('hex');
  const prettyPolicy = policy.replace('\n', '\n\n');
  fs.writeFileSync(path.join(root, POLICY), prettyPolicy);
  const instructionBlockSha256 = {};
  for (const file of ['AGENTS.md', 'CLAUDE.md']) {
    const formatted = readText(root, file).replace('## Project memory\n', '## Project memory\n\n');
    fs.writeFileSync(path.join(root, file), formatted);
    const block = formatted.match(/<!-- bas-more-project-memory:v2:start -->[\s\S]*?<!-- bas-more-project-memory:v2:end -->/)[0];
    instructionBlockSha256[file] = digest(block);
  }
  const config = JSON.parse(readText(root, CONFIG));
  config.policySha256 = digest(prettyPolicy);
  config.formatting = { schemaVersion: 1, tool: 'prettier', version: '3.9.6', sourcePolicySha256: digest(policy), instructionBlockSha256 };
  fs.writeFileSync(path.join(root, CONFIG), JSON.stringify(config, null, 4) + '\n');
}
test('preserves a reviewed formatter result and keeps later unrelated instruction edits', t => {
  const root = fixture(t);
  formattedFixture(root);
  fs.appendFileSync(path.join(root, 'AGENTS.md'), 'Maintainer note outside the managed block.\n');
  assert.equal(makePlan(root).changes.length, 0);
  assert.ok(readText(root, POLICY).includes('\n\n'));
});
test('rejects stale formatting receipts, policy edits and edited formatted instruction blocks', t => {
  const root = fixture(t);
  formattedFixture(root);
  assert.throws(() => planRepository({ repository, files: filesAt(root), policy: policy + 'New requirement\n' }), /source policy changed/);
  fs.appendFileSync(path.join(root, POLICY), 'Unreviewed policy edit\n');
  assert.throws(() => makePlan(root), /policy was edited/);
  const second = fixture(t);
  formattedFixture(second);
  fs.writeFileSync(path.join(second, 'AGENTS.md'), readText(second, 'AGENTS.md').replace('Use the graph workflow', 'Always build the graph workflow'));
  assert.throws(() => makePlan(second), /formatted instruction block was edited/);
});

const v1Block = nl => ['<!-- bas-more-project-memory:v1:start -->', '## Project memory',
  'Setup is enabled by the owner. Continue incomplete setup within this repository',
  'without asking again; preserve any working graph engine and its recorded pins.',
  '<!-- bas-more-project-memory:v1:end -->'].join(nl);
test('upgrades a v1 repository installation to v2 in place and a rerun is a no-op', t => {
  const root = fixture(t);
  const v1Policy = '# Comprehensive project memory\nversion 1 policy\n';
  fs.writeFileSync(path.join(root, 'AGENTS.md'), '﻿---\r\nname: kept\r\n---\r\n' + v1Block('\r\n') + '\r\n\r\nRead HANDOVER first.\r\n');
  fs.writeFileSync(path.join(root, 'CLAUDE.md'), 'Before.\n' + v1Block('\n') + '\nAfter.\n');
  fs.mkdirSync(path.join(root, '.project-memory'));
  fs.writeFileSync(path.join(root, POLICY), v1Policy);
  fs.writeFileSync(path.join(root, CONFIG), JSON.stringify({ schemaVersion: 1, managedBy: 'bas-more-project-memory', repository, choice: 'enabled',
    authorization: 'owner-approved-existing-repository-rollout', policySha256: hash(v1Policy), graphReadiness: 'requires-repository-validation' }));
  applyPlan(root, makePlan(root), path.join(root, 'backups'));
  const agents = readText(root, 'AGENTS.md'), claude = readText(root, 'CLAUDE.md');
  for (const text of [agents, claude]) {
    assert.ok(!text.includes('v1:start') && !text.includes('Setup is enabled by the owner'));
    assert.ok(text.includes('<!-- bas-more-project-memory:v2:start -->') && text.includes('Install graph engines, hooks or CI checks only when'));
  }
  assert.ok(agents.startsWith('﻿---\r\nname: kept\r\n---\r\n<!-- bas-more-project-memory:v2:start -->\r\n'));
  assert.ok(agents.endsWith('\r\n\r\nRead HANDOVER first.\r\n'));
  assert.ok(claude.startsWith('Before.\n') && claude.endsWith('\nAfter.\n'));
  const config = JSON.parse(readText(root, CONFIG));
  assert.equal(config.schemaVersion, 2);
  assert.equal(config.policySha256, hash(policy));
  assert.equal(config.authorization, 'install-only-for-setup-task-or-in-session-confirmation');
  assert.equal(readText(root, POLICY), policy);
  assert.equal(makePlan(root).changes.length, 0);
});
test('rejects mixed or duplicate v1/v2 markers', () => {
  assert.throws(() => findBlock(v1Block('\n') + '\n' + managedBlock('', 'x')), /duplicate/);
  assert.throws(() => findBlock('<!-- bas-more-project-memory:v1:start -->\n<!-- bas-more-project-memory:v2:end -->'), /Malformed/);
  assert.equal(findBlock('no block'), null);
});
test('upgrades v1 client rules to opt-in v2 rules without self-enrolment', t => {
  const profile = fixture(t);
  fs.mkdirSync(path.join(profile, '.codex'));
  fs.mkdirSync(path.join(profile, '.claude'));
  const legacy = 'User rules\n\n' + ['<!-- bas-more-project-memory:v1:start -->', '## Project memory on every project',
    'An eligible matching repository needs no new approval.', '<!-- bas-more-project-memory:v1:end -->', ''].join('\n') + 'Trailing rule\n';
  fs.writeFileSync(path.join(profile, '.claude', 'CLAUDE.md'), legacy);
  fs.writeFileSync(path.join(profile, '.codex', 'AGENTS.md'), legacy);
  for (const plan of clientPlan(profile)) applyPlan(plan.root, plan, path.join(profile, 'backups'));
  for (const file of [path.join(profile, '.claude', 'CLAUDE.md'), path.join(profile, '.codex', 'AGENTS.md')]) {
    const text = fs.readFileSync(file, 'utf8');
    assert.ok(text.startsWith('User rules\n\n<!-- bas-more-project-memory:v2:start -->') && text.endsWith('\nTrailing rule\n'));
    assert.equal(text.match(/bas-more-project-memory:v\d:start/g).length, 1);
    assert.ok(!/needs no new approval|obtain the approved policy/.test(text));
    assert.ok(text.includes('Ask before installing'));
  }
  assert.ok(clientPlan(profile).every(plan => plan.changes.length === 0));
});
