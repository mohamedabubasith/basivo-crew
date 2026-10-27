# basivo-crew

Turn an issue into a reviewed pull request, without being at your desk.

A Claude Code plugin that puts a crew of agents in your CI. Someone opens an issue; the
crew reads it against your actual code, writes the change, tests it, reviews it, and opens
a pull request with the verdicts attached. On every trigger, in your own runners, under
your branch protection.

The agents live here, versioned. The workflow files are fifteen lines each, because
`claude-code-action` installs this plugin into the run.

## Two tiers

| | Basic | Pro |
| :- | :- | :- |
| Agents | developer, reviewer | triage, architect, developer, tester, reviewer, security |
| Workflows | 2 | 4 |
| Issue triage | folded into the developer's prompt | its own pass, posts an action-item checklist |
| Tests | the project's own suite, run by the developer | tester writes what is missing and gates the pull request |
| Review | correctness | correctness + security, as inline comments |
| Follow-up on `@claude` | build workflow handles it | its own workflow, pushes to the same branch |
| Roughly, per issue | ~2 agent runs | ~6 agent runs |

Start on Basic. Move to Pro on a repo where a red main branch costs you something.

## Install

```bash
/plugin marketplace add mohamedabubasith/basivo-plugins
/plugin install basivo-crew@basivo
```

Then, in the repository you want it on:

```
/crew-init basic
```

That installs the workflows, creates the labels, and prints what is left for you to do.
`/crew-doctor` tells you why it is not running.

## What you have to do yourself

Two things, neither of which a plugin can do for you:

1. **Add the secret.** Settings → Secrets and variables → Actions:
   `CLAUDE_CODE_OAUTH_TOKEN`, from `claude setup-token` on your own machine. That bills
   against your Claude subscription. Prefer per-token API billing? Use
   `ANTHROPIC_API_KEY` and change the one line in each workflow.
2. **Allow it to open pull requests.** Settings → Actions → General → Workflow
   permissions → *Allow GitHub Actions to create and approve pull requests*.

## The flow

```
issue opened
   └─ triage ........ action items, grounded in real files        [pro]
      label crew:build  ← you, deliberately
         └─ architect .. the approach                             [pro]
            └─ developer ... the diff, and the project's checks
               └─ tester .... the missing tests, the suite        [pro]
                  └─ reviewer .. correctness
                     └─ pull request, verdicts in the body
                           │
pull request opened ───────┘
   └─ reviewer + security .. inline comments                      [pro: security]
      @claude on the thread
         └─ developer + tester .. pushed to the same branch
```

## Deliberate choices

**The build is behind a label.** `crew:build` is a human saying yes. Anyone who can open
an issue can otherwise spend your tokens and your runner minutes. One `if:` line turns it
off if you want every issue built — do that on a private repo, not a public one.

**Tests run inside the build job.** A pull request opened with the default `GITHUB_TOKEN`
does not trigger other workflows, so a separate test workflow would never fire on the
crew's pull requests. If you want your real CI on them, add a fine-grained PAT as
`BOT_TOKEN` and pass `github_token: ${{ secrets.BOT_TOKEN }}`.

**The agents cannot fake a pass.** Every agent that touches code is told, explicitly,
never to skip, delete, loosen or `continue-on-error` its way to green, and to report an
honest failure instead. The build opens a draft pull request and says what is red rather
than claiming success.

**Guardrails on every workflow.** `--max-turns`, a job `timeout-minutes`, a `concurrency`
group so a comment storm cannot fan out, and `[skip-crew]` in a title to opt out.

## Agents

Each is a subagent you can also call by hand in your editor —
`basivo-crew:reviewer`, `basivo-crew:triage`, and so on.

| Agent | Writes code | For |
| :- | :- | :- |
| `triage` | no | issue → ordered action items that name files |
| `architect` | no | the approach, the blast radius, the pattern to follow |
| `developer` | yes | the minimal diff, and the project's own checks, run for real |
| `tester` | yes | the test that fails if the change regresses; the suite |
| `reviewer` | no | defects with a traced failure path, blocking vs optional |
| `security` | no | untrusted input to sink, authz, secrets, supply chain |

## Cost

You are paying for agent runs and runner minutes. A Pro issue is roughly six agent runs
plus however many rounds the tester and reviewer send back. Keep issues specific, keep
`CLAUDE.md` short, and leave the label gate on.

## GitLab

Planned, not shipped. GitLab's Claude Code integration is beta and has no reusable
component: you hand-write a job that installs the CLI and runs `claude -p`, and
mention-driven triggers need a project webhook that calls the pipeline trigger API.
The agents in this plugin are platform-neutral and will carry over; the wiring will not.

## Licence

MIT
