# Seat 29: Document Intake

## Scope
Turns incoming documents (bills, purchase orders, receipts) into draft records with a confidence score and a human review queue.

## First task
Classify and extract 20 sample PDFs into draft Bills; report accuracy per field.

## Access
drive, email, accounting (draft only), forms

## Milestones
- 15 Nov 2026: first task delivered
- 30 Nov 2026: version 1, with a 12-task test suite
- 20 Dec 2026: integration run of all eight seats
- 31 Dec 2026: final

## Working rules
See the top-level README. Put your agent code, tests and notes in this folder; open a pull request for every change.

## Running the client
Stdlib only, Python 3.9 or later. Run these from this folder:

```
python -m unittest discover -s tests -t .
python -m intake.probe suryodaya keystone
```

The tests fake every network call. The probe needs a token for each system, in the environment or in the git-ignored `.env`, as `AGENTSWITCH_SURYODAYA_TOKEN` and `AGENTSWITCH_KEYSTONE_TOKEN`. It makes read-only calls and prints counts only.

`intake/mcp_client.py` is read-only for now. Its write guard allows a call only if the platform marks the tool READ, and it refuses everything else before sending, including posting tools such as `Bill.submit`. Writes will get their own reviewed path.

## When a call fails
- `AuthError`: the token was rejected or has expired (it lasts 7 days). Log in again, once. Ten wrong passwords in 15 minutes lock the login.
- `GuardRefused`: the guard is working and nothing was sent. Do not bypass it.
- `ToolError` or `TransportError`: post the system, your login name, the exact request and the reply in the seat group. Leave out any password or token.

## Reading documents
Needs `pip install -r requirements.txt`. This works on local PDFs and does not use the platform.

```
python -m intake.extract local/samples/*.pdf --out local/predictions.json
```

Each document gets a type, its fields, flags, and a rule score from 0 to 1 (not a probability). The rules work out the type from who issued the document and who it is billed to, because a bill and our own sales invoice can both say TAX INVOICE. A stated total that does not add up is kept as stated and flagged. A missing value stays empty and is never guessed.

Every result is a proposal, and a person approves any record. `needs_review` only marks what a person should look at first.

Keep the output in `local/`, which is git-ignored, because it holds document data.

## Scoring
A person runs this, because the answer key must stay out of the agent's reach. Keep the key outside this repository. The scorer reads it from the zip in memory and prints totals and field names only, never an answer.

```
python -m intake.score --describe --key PATH/TO/KEY.zip
python -m intake.score --labels --key PATH/TO/KEY.zip
python -m intake.score local/predictions.json --key PATH/TO/KEY.zip
```
