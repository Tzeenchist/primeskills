# Mutator

Read before letting a mutation tool do step 7 instead of a hand mutation.
Measured 2026-10-27 on `unclebob/mutator` `a5a0cb8` (PS-112); other tools
earn the same four checks before their output counts.

## When its run counts

- **The test command is named.** `--test-command "<project interpreter> -m
  pytest -q <affected tests>"`. Left to itself it picks an interpreter and a
  runner, and a wrong pick fails the baseline for every file.
- **Coverage is given or switched off.** `--no-coverage`, or
  `--use-existing-coverage` with a report you just made. Without either it
  installs `coverage` into the project's interpreter — into the system
  `python3` when the project has no `.venv` — and on failure marks every
  mutant uncovered and still exits 0.
- **Something ran.** Read the table: killed + survived above zero. A run
  where every site is uncovered proved nothing, whatever the exit code.
- **The target is disposable.** It writes `.metrics/` and `target/` into the
  tree and links the rest of the project into each worker: a test that writes
  files writes them into the real tree. Run it in the throwaway worktree step
  7 already asks for, and remove both directories after (G7).

## Reading it

Exit 3 means a mutant survived: name the missing test or why the mutant is
equivalent, as step 7 does. Exit 2 means the baseline failed and nothing was
mutated. It sees files by extension only — a script without `.py` is not in
the run, so say which files it left out.
