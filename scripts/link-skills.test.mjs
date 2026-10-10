import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const script = path.join(path.dirname(fileURLToPath(import.meta.url)), 'link-skills.sh');

// The script derives REPO from its own location and reads $HOME, so a copy of it
// inside a fixture repo plus a fixture HOME keeps every run away from the real
// checkout and the real ~/.claude/skills. The fixture repo ships one skill,
// `research`, which is the name the tests collide with.
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'link-skills-test-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.mkdirSync(path.join(root, 'repo/scripts'), { recursive: true });
  fs.copyFileSync(script, path.join(root, 'repo/scripts/link-skills.sh'));
  fs.mkdirSync(path.join(root, 'repo/skills/engineering/research'), { recursive: true });
  fs.writeFileSync(path.join(root, 'repo/skills/engineering/research/SKILL.md'), '# research\n');
  fs.mkdirSync(path.join(root, 'home/.claude/skills'), { recursive: true });
  fs.mkdirSync(path.join(root, 'home/.agents/skills'), { recursive: true });
  return root;
}
const link = root => execFileSync('bash', [path.join(root, 'repo/scripts/link-skills.sh')], {
  env: { ...process.env, HOME: path.join(root, 'home') },
  encoding: 'utf8',
  stdio: 'pipe'
});

test('refuses to delete a real directory that did not come from this repo', t => {
  const root = fixture(t);
  const victim = path.join(root, 'home/.claude/skills/research');
  fs.mkdirSync(victim);
  fs.writeFileSync(path.join(victim, 'my-notes.md'), 'irreplaceable\n');
  assert.throws(() => link(root), err => {
    assert.equal(err.status, 1);
    assert.match(err.stderr, /already exists and is not a symlink/);
    assert.ok(err.stderr.includes(victim));
    // The refusal must not also report a link it did not make.
    assert.doesNotMatch(err.stdout, /^linked research/m);
    return true;
  });
  assert.equal(fs.readFileSync(path.join(victim, 'my-notes.md'), 'utf8'), 'irreplaceable\n');
  assert.equal(fs.lstatSync(victim).isDirectory(), true);
  assert.equal(fs.lstatSync(victim).isSymbolicLink(), false);
});

test('relinks idempotently when the target is a symlink the script made', t => {
  const root = fixture(t);
  link(root);
  link(root);
  for (const harness of ['.claude', '.agents']) {
    const target = path.join(root, 'home', harness, 'skills/research');
    assert.equal(fs.lstatSync(target).isSymbolicLink(), true);
    assert.equal(fs.readlinkSync(target), path.join(root, 'repo/skills/engineering/research'));
    // The re-run must replace the link in place. Without `-n`, ln would follow the
    // existing link and write research/research into the repo's own skill directory.
    assert.equal(fs.existsSync(path.join(target, 'research')), false);
  }
});
