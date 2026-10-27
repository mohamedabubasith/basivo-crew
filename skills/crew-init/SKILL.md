---
name: crew-init
description: Set up the Basivo Crew in a repository — pick Basic or Pro, install the workflow files, create the labels, and print the exact secret checklist. Use when someone wants automated issue-to-pull-request agents on a repo, or says "set up the crew".
argument-hint: "[basic|pro]"
---

# /crew-init

Install the crew into the repository the user is in. You are doing the setup; do not
hand them a tutorial.

## 1. Check where you are

Run `git remote -v` and `gh auth status`. If this is not a git repository with a GitHub
remote, say so and stop — there is nothing to wire up.

Note the default branch (`gh repo view --json defaultBranchRef`). The workflows run on
pull requests into it.

## 2. Pick the tier

If `$1` is `basic` or `pro`, use it. Otherwise ask once, with the trade-off:

- **Basic** — developer + reviewer. Two workflows, ~2 agent runs per issue. Start here on
  a small or personal repo.
- **Pro** — triage, architect, developer, tester, reviewer, security. Four workflows,
  ~6 agent runs per issue, a tester gate before the pull request opens. Worth it where a
  red main branch actually costs something.

Say plainly that Pro costs several times more per issue, because it runs several times
more agents.

## 3. Install the workflows

Copy the chosen tier's files into `.github/workflows/`:

```
${CLAUDE_PLUGIN_ROOT}/templates/github/<tier>/*.yml
```

Before writing, read any existing `.github/workflows/crew-*.yml`. If one exists, show
the diff and ask before overwriting — never silently replace a workflow someone edited.

Then adapt what you copied to this repository, and say what you changed:

- If the repo's checks are not `npm run lint` / `build` / `test`, the prompts say "this
  project's own lint, build and test commands" — that is deliberate, leave it. Only
  hardcode a command if discovery is genuinely ambiguous.
- If the default branch is not `main`, nothing needs changing; the action reads it.
- If this is a monorepo, add a `paths:` filter to the review workflow so unrelated
  packages do not trigger a run.

## 4. Install the per-repo config

Copy `${CLAUDE_PLUGIN_ROOT}/templates/.basivo-crew.yml` to the repo root and fill it in
from what you can see in this repository — real globs for its real directories, real
check commands from its `package.json` or `Makefile`, and `off_limits` for anything that
should never be edited by an agent (CI config, infra, migrations, lockfiles). Delete the
example entries that do not apply; a config full of irrelevant rules is worse than none.

Copy `${CLAUDE_PLUGIN_ROOT}/templates/learnings/learnings.md` to
`.basivo-crew/learnings.md`. That file is how the crew stops repeating a finding someone
has already dismissed, and the follow-up workflow appends to it on its own.

## 5. Write down how to build this project

This is the highest-leverage thing in the whole setup, and the step people skip. Every
agent reads `CLAUDE.md` or `AGENTS.md`, and the quality of what the crew produces tracks
the quality of that file more than anything else here.

Check whether one exists. If it does, read it and add only what is missing. If it does
not, create `AGENTS.md` and keep it short — a page, not an essay:

- the install command, and anything non-obvious about it
- lint, typecheck, test and build commands, exactly as a contributor runs them
- how to run one test, not the whole suite
- the conventions a newcomer gets wrong in this repo
- what not to touch, and why

Show the user what you wrote and let them correct it. They know things about their own
project that are not in the tree.

## 6. Create the labels

```bash
gh label create crew:build      --color 6d4aff --description "Hand this issue to the crew" --force
gh label create crew:ready      --color c4b5fd --description "Triaged, ready for the crew" --force
gh label create crew:needs-info --color fbbf24 --description "Triage needs more from the reporter" --force
```

`crew:ready` and `crew:needs-info` are Pro-only; skip them on Basic.

## 7. Print the checklist

The user has to do these — you cannot. Print exactly this, filled in for their repo:

```
Before the crew can run:

1. Secret — Settings > Secrets and variables > Actions > New repository secret
     Name:  CLAUDE_CODE_OAUTH_TOKEN
     Value: run `claude setup-token` on your machine and paste the token
   (Or use ANTHROPIC_API_KEY instead and change that one line in each workflow.)

2. Setting — Settings > Actions > General > Workflow permissions
     [x] Allow GitHub Actions to create and approve pull requests

3. Try it — open an issue, then add the `crew:build` label.
```

Then tell them two things they will otherwise learn the hard way:

- A pull request the crew opens with the default `GITHUB_TOKEN` **does not trigger other
  workflows**. That is why the tests run inside the build job. If they want their own CI
  to run on crew pull requests, they need a fine-grained PAT as `BOT_TOKEN` and
  `github_token: ${{ secrets.BOT_TOKEN }}` in the workflows.
- Anyone who can open an issue can spend tokens if they remove the label gate. The
  `crew:build` label is the gate; keep it on a public repo.

## 8. Commit

Commit the workflows, `.basivo-crew.yml`, `.basivo-crew/learnings.md` and any
`AGENTS.md` change on a branch, and show them the diff. Do not push to the default branch
without asking.

Then say, in one line each, what they can tune later: `profile` in `.basivo-crew.yml` if
the reviewer is too loud or too quiet, and `path_instructions` for the rules a reviewer
on their team would know and a stranger would not.
