# Seat 29 harness checks

Checks for the course harness, which runs them on a throwaway copy of each instance. The format is in `34-eval-harness/TASK_FORMAT.md`. This is not yet the 12-task suite.

## Setup checks

| Check | What it tells us |
|---|---|
| `system_and_settings` | Python version, operating system and whether all run settings arrive |
| `packages_installed` | `requirements.txt` installs and works |
| `login_and_read` | The seat token logs in and can read on the copy |
| `guard_refuses_posting` | Our client refuses `Bill.submit`, sends nothing and the Bill count stays the same |
| `model_reads_images` | Whether the run's model names the colour of two test images correctly, which decides how we handle scans |

## Intake checks

| Check | What it tells us |
|---|---|
| `unit_tests_pass` | All of `29-document-intake/tests` pass on the run's system |
| `risky_tools_refused` | 14 posting, payment, sending and write tools are refused by the read-only client, none is sent, and the Bill count stays the same |
| `samples_on_copy` | The 20 course samples download from the copy, and each matches our copy by sha256 |
| `reader_on_copy_samples` | Our reader gives the same results on them as it does locally, compared by a hash of the scored fields and flags |
| `vendor_check_on_copy` | The vendor check reads every Party and Bill on the copy and gives each vendor bill a result |
| `extract_on_copy` | The platform's `extract` runs on each sample through our write path, and creates no Bill |
| `readers_compared` | For each field, how often the platform's reader and ours agree |
| `accept_one_draft` | `accept` on one clean vendor bill creates exactly one Bill, as a draft. A retry with the same id creates no second Bill, and `Bill.submit` stays refused |

## Writes

The last three checks write, through `intake/write_path.py`. It allows only `extract`, `accept` and a `Party.create` labelled `[seat29-harness]`. It refuses unless the run has `AGENTSWITCH_RUN_ID` and its base URL is neither live system, so these checks do nothing outside a harness copy. On a copy, writes are thrown away afterwards. The approver recorded for each write is the harness run.

`accept` needs a vendor id. None of the sample vendors has a Party, so on the copy the check creates one labelled `[seat29-harness]` first.

## Evidence

Evidence holds counts, yes/no answers, field names and the model's short answer about our own test images. It never holds document values, tokens or record contents. Extra counts go to the run log with the prefix `[seat29]`.

`expected_samples.py` holds a sha256 per sample file and a hash of our reader's results. Neither holds a document value or anything from the answer key.

## Running the tests

From the repo root:

```
python -m unittest harness.test_setup_check harness.test_intake_checks
python -m harness.runner --only intake --out results.json
```

The second command needs `AGENTSWITCH_TOKEN`, `AGENTSWITCH_BASE_URL` and `AGENTSWITCH_INSTANCE`. Outside a harness run, the write checks report "not tried".
