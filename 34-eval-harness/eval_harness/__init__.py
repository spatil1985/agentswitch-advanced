"""Seat 34 eval harness: runs suites of tasks against an agent under test and grades the platform outcome.

Vocabulary (from Anthropic's "Demystifying evals for AI agents" and course session 18):
    suite  -> tasks       what to ask, and how success is judged          (suite.py)
    trial                 one attempt at one task, saved before scoring  (trial.py)
    graders               code checks of the outcome (platform state)    (graders.py)
    scorer                grader results + trial facts -> score fields   (scorer.py)
    results               the course's results.json                      (results.py)

The eval harness never imports the agents under test, and they never import it (import-linter checks this).
"""
