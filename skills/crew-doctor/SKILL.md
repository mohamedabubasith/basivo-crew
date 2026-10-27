---
name: crew-doctor
description: Check whether the Basivo Crew is correctly wired in this repository — workflows, secret, labels, repo settings, recent runs — and report what is broken. Use when the crew did not respond to an issue or a pull request, or to verify a fresh setup.
---

# /crew-doctor

Find out why the crew is not working. Check everything, then report once.

## Checks

Run these and collect the results before saying anything:

1. **Workflows present** — `ls .github/workflows/crew-*.yml`. Which tier do they look
   like? Are they on the default branch? A workflow on a feature branch does not run for
   `issues` events.
2. **Secret** — `gh secret list`. Is `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`
   there, and does it match what the workflows reference? You can see that a secret
   exists, never its value — so an expired or wrong token looks identical to a good one
   here. Note that limit rather than claiming the token is valid.
3. **Workflow permissions** — `gh api repos/{owner}/{repo}/actions/permissions/workflow`.
   `can_approve_pull_request_reviews` must be true for the crew to open pull requests.
4. **Labels** — `gh label list`. Is `crew:build` there, spelled exactly?
5. **Recent runs** — `gh run list --limit 10`. For any failure,
   `gh run view <id> --log-failed`. Read the actual error; do not guess from the name.
6. **Config sanity** — if `.basivo-crew.yml` exists, do its `path_instructions` globs
   match any real file (`git ls-files` against each glob)? A glob that matches nothing is
   a rule that silently never applies, and it is the most common thing wrong with these
   files. Does `.basivo-crew/learnings.md` exist, and does an entry in it explain a
   finding the user expected to see and did not?
7. **Trigger reality check** — if the user says nothing happened at all, check that the
   event could have fired: the label was added (not just mentioned), the comment
   contains `@claude`, the pull request is not a draft, the title has no `[skip-crew]`,
   and the actor has write access.

## Report

```
## Crew doctor: <tier> tier

✅ <check> — <what you found>
❌ <check> — <what is wrong>
   Fix: <the exact command or the exact UI path>
⚠️  <check> — <what you cannot verify from here>
```

Lead with the one thing most likely to be the cause, then the rest. If every check
passes and the crew still did not run, say so and give them the most useful next step:
`gh run list --workflow=crew-build.yml` and the run log — the answer is in there, not in
more guessing.

Do not fix anything without asking first. A broken crew setup is cheap; a workflow file
rewritten under someone is not.
