# Tasks: add --verbose flag

- [x] 1. Add `--verbose` (store_true) to the argparse parser in `main.py`.
- [x] 2. When verbose, print debug info to stderr at session start: model,
      thread id, and sessions DB path.
- [x] 3. When verbose, print per-turn elapsed time to stderr after each agent
      response in the REPL loop.
