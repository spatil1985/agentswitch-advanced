# Seat 29 setup check

A small run to confirm our harness setup before the 12-task suite is ready. It follows `34-eval-harness/TASK_FORMAT.md`.

| Check | What it tells us |
|---|---|
| `system_and_settings` | Python version, operating system and whether all run settings arrive |
| `packages_installed` | `requirements.txt` installs and works |
| `login_and_read` | The seat token logs in and can read on the copy |
| `guard_refuses_posting` | Our client refuses `Bill.submit`, sends nothing and the Bill count stays the same |
| `model_reads_images` | Whether the run's model names the colour of two test images correctly, which decides how we handle scans |

Evidence holds counts, yes/no answers and the model's short answer about our own test images.

Run the tests from the repo root:

```
python -m unittest harness.test_setup_check
```
