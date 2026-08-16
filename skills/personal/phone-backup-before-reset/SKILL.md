---
name: phone-backup-before-reset
description: Produce a full pre-wipe backup checklist for a phone before a factory reset, covering the data that no backup tool captures. Use when the user is about to factory reset, wipe, trade in, or migrate a phone and wants to be sure nothing is lost.
---

# Phone Backup Before Reset

A factory reset destroys the device's encryption keys along with its data. Cloud
sync and vendor tools cover most of it — the job of this skill is the remainder,
because every item in that remainder fails **silently**. The backup tool reports
success and the data is still gone.

## Ask first

Three answers change every subsequent step. Ask them together, don't guess:

1. **Platform** — iOS or Android, and which manufacturer (Samsung/One UI, Pixel,
   etc.). Menu paths and vendor tooling differ completely.
2. **Destination** — cloud, local computer, or both. Default to recommending
   both: cloud restores most easily, local survives an account lockout.
3. **Same device or new one** — restoring to the same handset skips eSIM
   transfer and carrier re-activation; moving to a new one adds them.

## The rule that matters

Order the work by **what is unrecoverable**, not by what is easiest. A checklist
that opens with "back up your photos" buries the items that actually end in
permanent loss. Lead with those, and make the user verify them before wiping.

## The silent failures

These are the ones people discover too late. Confirm each explicitly — see
[CHECKLIST.md](./CHECKLIST.md) for the full phase-by-phase content.

| Data | Why it's lost | What to do instead |
| --- | --- | --- |
| 2FA / TOTP seeds | Stored locally, never in a device backup | Turn on the authenticator's cloud sync, or export the QR to another device. Download account backup codes. |
| Passkeys | Bound to device hardware, not exportable | Confirm every account has a second credential before wiping |
| Secure Folder (Samsung) | Own encryption key, dies with the reset; excluded from Smart Switch and from cloud backup since 2021 | Move contents out to normal storage by hand, then copy off-device |
| Signal (Android) | No cloud backup at all — a local file on the storage being erased | Back up to file, copy it to a computer, save the 30-digit passphrase off-device |
| WhatsApp | Separate Google Drive backup, not the OS backup | Force a manual backup; save the end-to-end encryption key |
| Vendor health/notes data | Only syncs if explicitly enabled | Check the sync toggle rather than assuming |

## Procedure

1. **Ask the three questions** above.
2. **Verify version-specific behaviour** before writing anything. Reset-screen
   options, backup-tool exclusions and app backup models change between OS
   releases — check current sources rather than writing from memory, and say
   which build the paths assume.
3. **Draft the checklist in phases**, in this order: unrecoverable items →
   cloud backups → local copy → things no backup touches → verification →
   wipe and restore sequence.
4. **Include a verification phase.** This is the step users skip and the one
   that catches a failed backup while it can still be fixed. The strongest test
   for 2FA: sign in to the account from another device with the phone face down.
5. **Get the restore order right.** Some apps only offer to restore during their
   first launch after install — restoring them late means one wasted attempt.
6. **Render it as an Artifact**, not terminal text. It gets worked through over
   hours, away from the machine. Make the items tickable and lead with the
   unrecoverable ones.

## Output

An HTML artifact with:

- A progress gate that stays red until the unrecoverable items are ticked
- Severity on every item (unrecoverable / important / routine) as visible form,
  not just a word
- Exact settings paths in monospace, distinct from prose
- A closing reference table of where each kind of data actually lives
- A note on which OS version the paths assume

Keep the local backup for a couple of weeks after the restore — missing data
usually surfaces days later.
