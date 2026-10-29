# Contributing

This is early native-recompilation research. Contributors with PPU/SPU, PS3 ABI, SPURS, RSX/Vulkan, Windows toolchain or reverse-engineering experience are welcome. Documentation and build reproducibility improvements are valuable too.

## Start here

1. Read [STATUS](docs/STATUS.md), [BUILDING](docs/BUILDING.md) and the roadmap issue.
2. Pick one `help wanted` issue or open a focused proposal before a large architectural change.
3. Work on a branch and submit a pull request describing the actual problem, change and evidence.

Use Issues for reproducible bugs and bounded implementation work. Use Discussions for setup questions, research hypotheses and architecture ideas. English or Portuguese is welcome.

## Project constraints

- Windows x86-64 and Vulkan are the present target. Preserve the native AOT execution path.
- Do not add a CPU interpreter/JIT fallback, fabricated job completion, skipped guest work or a placeholder image presented as a game frame.
- Preserve original user inputs. Keep generated code, captures and game data under ignored local directories.
- Do not upload game executables, disc/update data, generated instruction bodies, firmware, SDKs, keys, dumps or credentials in issues, PRs, attachments or Git history.
- Treat compiled counts, execution, drawing and gameplay as separate claims. Mark uncertain findings as hypotheses.
- Include upstream credits and license notices for any adapted code. Use official sources when comparing hardware/service behavior.

## Validation

Prefer the smallest check that can falsify the proposed fix. For boot work, build the changed batch and make one bounded run. Preserve the observed target, LR, thread, exit code and relevant redacted diagnostics locally. Do not repeatedly run an unchanged build or spend time on broad tests unrelated to the change.

PRs should state what was actually tested and what was not. The public CI checks source hygiene, Python syntax and patch consistency; it does not contain game data or prove that GT5 boots.

## Sharing diagnostics

Report the game identifier/update, OS, GPU/driver, dependency versions and the relevant service or native stop address. Share only short, reviewed diagnostics; remove account names, absolute personal paths, keys and binary contents. Ask before attaching a large artifact.

## Conduct

Be respectful and specific. Critique code and evidence, not people. No harassment, personal data disclosure, piracy links or demands for ETAs. AI-assisted contributions are welcome when disclosed and reviewed; the contributor is responsible for understanding and explaining the change.

Unless explicitly stated otherwise, original contributions are submitted under the repository's MIT license. Existing third-party notices remain applicable.
