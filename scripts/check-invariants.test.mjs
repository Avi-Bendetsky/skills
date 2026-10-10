import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const repository = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const script = path.join(repository, 'scripts', 'check-invariants.sh');

// Public buckets are promoted (README + manifest); private ones must be in neither.
const skills = {
  engineering: ['alpha'],
  productivity: ['beta'],
  misc: ['gamma'],
  personal: ['secret'],
  'in-progress': ['draft'],
  deprecated: []
};
const publicBuckets = ['engineering', 'productivity', 'misc'];
const promoted = ['./skills/engineering/alpha', './skills/productivity/beta', './skills/misc/gamma'];
const description = 'does a thing properly.';

function write(root, file, content) {
  fs.mkdirSync(path.dirname(path.join(root, file)), { recursive: true });
  fs.writeFileSync(path.join(root, file), content);
}

function writeManifest(root, entries) {
  // `repository` and `keywords` stay path-adjacent on purpose: the checker must
  // read only the `skills` array, not every quoted string in the file.
  write(root, '.claude-plugin/plugin.json', JSON.stringify({
    name: 'fixture',
    repository: 'https://github.com/example/skills',
    keywords: ['skills'],
    skills: entries
  }, null, 2) + '\n');
}

// A synthetic tree rather than a copy of the repo: fast, and independent of real skill content.
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'check-invariants-test-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const rootReadme = [];
  for (const [bucket, names] of Object.entries(skills)) {
    const bucketReadme = [`# ${bucket}`, ''];
    for (const name of names) {
      write(root, `skills/${bucket}/${name}/SKILL.md`, `# ${name}\n`);
      bucketReadme.push(`- [${name}](./${name}/SKILL.md) ${description}`);
      if (publicBuckets.includes(bucket)) rootReadme.push(`- [${name}](./skills/${bucket}/${name}/SKILL.md) ${description}`);
    }
    write(root, `skills/${bucket}/README.md`, bucketReadme.join('\n') + '\n');
  }
  write(root, 'README.md', ['# Fixture', '', ...rootReadme, ''].join('\n'));
  writeManifest(root, promoted);
  // The script derives its repo root from dirname "$0", so it cannot be aimed with cwd or an
  // env var. A symlink (not a copy) makes "$0" resolve into the fixture while still running the
  // real file, so this test cannot go stale against the script it guards.
  fs.mkdirSync(path.join(root, 'scripts'));
  fs.symlinkSync(script, path.join(root, 'scripts', 'check-invariants.sh'));
  return root;
}

function run(root) {
  try {
    const stdout = execFileSync('bash', [path.join(root, 'scripts', 'check-invariants.sh')], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    return { status: 0, stdout };
  } catch (err) {
    return { status: err.status, stdout: String(err.stdout) };
  }
}

const withEntries = (root, extra, base = promoted) => {
  writeManifest(root, [...base, ...extra]);
  return run(root);
};

test('a clean tree passes, so the array-scoped reader adds no false positives', t => {
  const result = run(fixture(t));
  assert.equal(result.status, 0, result.stdout);
  assert.match(result.stdout, /OK/);
});

test('control: the byte-exact spelling of a private skill is rejected', t => {
  const result = withEntries(fixture(t), ['./skills/personal/secret']);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /unpromoted skills\/personal\/secret is listed/);
});

test('a trailing slash does not hide an unpromoted skill from rule 4', t => {
  const result = withEntries(fixture(t), ['./skills/in-progress/draft/']);
  assert.equal(result.status, 1, result.stdout);
  assert.match(result.stdout, /unpromoted skills\/in-progress\/draft is listed/);
});

test('a missing ./ prefix does not hide an unpromoted skill from rules 4 or 6', t => {
  const result = withEntries(fixture(t), ['skills/personal/secret']);
  assert.equal(result.status, 1, result.stdout);
  // Both: rule 4 must see it, and rule 6 must flag the spelling it used to be invisible to.
  assert.match(result.stdout, /unpromoted skills\/personal\/secret is listed/);
  assert.match(result.stdout, /is not written as '\.\/skills\/<bucket>\/<skill>'/);
});

// Each of these used to exit 0 with an unpromoted skill published.
for (const [label, spell] of [
  ['an extra ./ segment', () => './skills/./personal/secret'],
  ['a doubled slash', () => './/skills/personal/secret'],
  ['a .. segment', () => './skills/in-progress/../in-progress/draft'],
  ['an absolute path', root => path.join(root, 'skills', 'personal', 'secret')]
]) {
  test(`non-canonical spelling is rejected: ${label}`, t => {
    const root = fixture(t);
    const result = withEntries(root, [spell(root)]);
    assert.equal(result.status, 1, result.stdout);
    assert.match(result.stdout, /is not written as '\.\/skills\/<bucket>\/<skill>'/);
  });
}

test('an entry that resolves to no skill still fails', t => {
  const result = withEntries(fixture(t), ['./skills/engineering/does-not-exist']);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /has no SKILL\.md/);
});

test('a missing public entry still fails rule 2, so the positive direction is not loosened',  t => {
  const result = withEntries(fixture(t), [], promoted.slice(1));
  assert.equal(result.status, 1);
  assert.match(result.stdout, /skills\/engineering\/alpha is missing from/);
});
