# Checklist content

Phase-by-phase source material for the artifact. Paths below are Samsung One UI
6+ (written against a Galaxy Z Fold 4, restoring to the same device). Re-verify
against the user's actual platform and build before using — this is a starting
point, not a fixed script.

## 01 — The ones no backup will save

**Get 2FA codes off the phone.** Authenticator seeds are stored locally and are
never included in a device backup. Worst case this locks the user out of the
Google account they need to clear Factory Reset Protection on the wiped phone.
Confirm the cloud-sync icon in Google Authenticator is green; otherwise
`Menu › Transfer accounts › Export accounts` and photograph the QR with another
device. Repeat for Microsoft Authenticator, Authy, Steam Guard, in-app bank
tokens. Download backup codes for critical accounts from a computer.

**Empty Secure Folder by hand.** Excluded from Smart Switch, and Samsung
discontinued its cloud backup in 2021. The key is destroyed by the reset, so a
complete Smart Switch archive restores everything except this.
`Secure Folder › long-press files › Move out of Secure Folder`, then copy them
off in phase 03. Apps and accounts inside must be set up again from scratch.

**Back up Signal, save the passphrase.** No cloud backup on Android — the backup
is a file on the storage about to be erased. Signal cannot reset or recover the
passphrase. `Signal › Settings › Chats › Chat backups`. Copy the folder to a
computer. Restoring only works during the first launch after reinstall.

**Force a WhatsApp backup.** Its Google Drive backup is separate from the OS
backup; the last automatic run may be days old.
`WhatsApp › Settings › Chats › Chat backup › Back up now`. If end-to-end
encrypted backups are on, the password or 64-digit key cannot be reissued.

## 02 — Fill both clouds

Google and Samsung back up different things; neither is a superset of the other.

- `Settings › Google › All services › Backup › Back up now` — apps and their
  data (only apps that opt in), SMS/MMS, call history, Wi-Fi networks and
  passwords, device settings. Wait for the timestamp to update.
- Google Photos — the profile icon must read **Backup complete**, not a pending
  count. A full storage quota stalls uploads quietly.
- `Settings › Samsung Cloud › Back up data` — home and cover screen layouts,
  app pairs, Flex mode settings, Samsung Notes, calendar, contacts, alarms,
  call logs, messages. 15 GB free.
- `Samsung Health › Settings › Sync with Samsung Cloud` — off by default. Also
  check Samsung Pass and Internet bookmarks.

## 03 — Make the local copy

**Smart Switch to a computer.** Needs a real USB-C *data* cable; a charge-only
cable fails with no useful error. Set an encryption password and record it —
there is no recovery. Backups land in
`C:\Users\<you>\Documents\Samsung\SmartSwitch\backup` or
`~/Documents/Samsung/SmartSwitch/backup`.

**Also copy folders as plain files.** Smart Switch archives are opaque and
occasionally refuse to restore. Set USB mode to file transfer and pull Internal
storage — at minimum DCIM, Download, Documents, Pictures, Movies, Music, and the
WhatsApp and Signal folders.

**Not included in Smart Switch:** Secure Folder, Google account credentials,
downloaded themes and store wallpapers, DRM-protected downloads, and apps
blocked for security reasons (Samsung Wallet, Galaxy Wearable).

## 04 — Things no backup touches

- **Passkeys** — hardware-bound and destroyed. If a passkey is an account's only
  credential, that account is unreachable after the reset.
- **Factory Reset Protection** — setup demands the Google account that was on the
  device. Reset from Settings while still signed in; removing the account first
  is unnecessary and disables Find My Device.
- **eSIM** — One UI 6+ shows a separate erase-eSIM option on the reset screen,
  normally off by default; leave it unticked. Older builds wipe it regardless.
  Confirm the carrier can re-issue a QR either way.
- **Odds and ends** — game saves not linked to an account, custom ringtones,
  Bixby routines, learned keyboard dictionary, call recordings, offline Netflix
  and Spotify downloads, contacts stored on the physical SIM. Banking and
  government apps de-register the device and need re-verifying.

## 05 — Verify before committing

The step everyone skips, and the last moment anything can be fixed.

- **Sign in to the account from another device with the phone face down.** The
  only real test that the 2FA codes survive. If it fails, stop and fix it.
- Open the backup folder on the computer — dated today, plausible size (tens of
  GB, not tens of MB). Spot-check photos in a browser.
- Record off-device: Google password, Samsung password, Smart Switch encryption
  password, Signal's 30-digit passphrase, WhatsApp key.

## 06 — Wipe, then restore in order

Charge past 50%. `Settings › General management › Reset › Factory data reset`.
Read the accounts list, scroll to the bottom, check the eSIM option is unticked.

Restore sequence — two apps only offer to restore on first launch, one attempt:

1. Take the "bring data from old device" offer at first boot; restore Smart
   Switch by cable.
2. Sign in to Google — apps, settings, Authenticator codes.
3. Sign in to Samsung — home/cover screen layouts, Notes, Health, Pass.
4. Install WhatsApp, restore **before** finishing setup.
5. Copy the Signal folder back to internal storage, install Signal, enter the
   30-digit passphrase **before** submitting the phone number.
6. Re-add Wallet cards, rebuild Secure Folder, re-authorise banking apps.

Keep the local backup for a fortnight.

## Reference table

| Data | Covered by | Catch |
| --- | --- | --- |
| Photos & video | Google Photos | Must read "Backup complete" |
| Contacts, calendar | Google + Samsung Cloud | SIM-stored contacts are separate |
| SMS, call log | Google backup, Samsung Cloud | Do both |
| App data | Google backup | Only apps that opt in — many don't |
| Home & cover screen | Samsung Cloud | Fold app pairs ride along |
| WhatsApp | Own Drive backup | Encryption key can't be reissued |
| Signal | Local file only | No cloud; passphrase unrecoverable |
| 2FA seeds | Authenticator cloud sync | Nothing else captures them |
| Passkeys | Nothing | Hardware-bound, destroyed |
| Secure Folder | Nothing | Move contents out by hand |
| Samsung Health | Samsung Cloud | Only if sync was enabled |
| Wallet cards | Nothing | Tokens wiped; re-add after |
| eSIM profile | Reset-screen option | Leave "erase eSIM" unticked |

## Sources

Version-specific behaviour worth re-checking each time it's used:

- [Samsung — back up and restore](https://www.samsung.com/us/support/answer/ANS10002780/)
- [Signal — Android on-device backups](https://support.signal.org/hc/en-us/articles/10066926526362-Android-On-device-Backups)
- [Google — Authenticator codes](https://support.google.com/accounts/answer/1066447?hl=en&co=GENIE.Platform%3DAndroid)
- [Samsung Community — eSIM and factory reset](https://us.community.samsung.com/t5/Fold-Flip-Phones/Does-a-factory-reset-remove-the-eSIM/td-p/2804125)
