# Project workflow

- User preference: after every completed update, run relevant checks and publish
  the updated source and versioned RPM to Tubix777/anvil-control on GitHub.
- Keep experimental hardware support explicitly labeled. Do not claim a device
  works based only on a successful command; record real readback/test evidence.
- Never commit credentials, personal logs, serial numbers or diagnostic exports.
- Privileged fan writes belong only in the standalone, root-owned packaged helper.
  Preserve its board/channel restrictions, validation, backup and rollback behavior.
