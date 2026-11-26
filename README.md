# Odin plugins for Claude

Claude Code plugins for [Odin](https://www.odinhelp.com) — the help desk, RMM
and PSA platform.

> This repository is **generated**. It is assembled from
> `.claude/skills/odin-api/` in the Odin platform repo and pushed here by CI.
> Open issues and pull requests against the platform repo, not this mirror —
> changes made here are overwritten on the next sync.

## Install

```
/plugin marketplace add RivetedTech/odin-claude-plugin
/plugin install odin-api@odin
```

Not using Claude Code plugins? The same skill installs with one line:

```
curl -fsSL https://www.odinhelp.com/skill/install.sh | bash
```

## Set it up

The skill talks to Odin with a **Personal Access Token**, which you create in
the Odin dashboard under **Profile → Personal Access Tokens**. Export it along
with the API address for your environment:

```bash
export ODIN_API_TOKEN="opat_..."
export ODIN_API_BASE_URL="https://api.odinhelp.com"
```

Then confirm it works:

```bash
scripts/odin preflight
```

If you are already signed in to Odin, the dashboard's Claude skill button hands
you a download with both values filled in.

## What the token can do

The token authenticates **as you**, with your live role and permissions — it can
do through the API exactly what you can do in the dashboard, and no more. A
`403` means your account lacks that access, not that the skill is broken.

Treat it like a password. Never commit it or paste it into a shared channel;
revoke it any time from the same Profile screen. Writes hit real data, so point
`ODIN_API_BASE_URL` at a dev environment while you experiment.

## Full documentation

<https://www.odinhelp.com/skill/>
