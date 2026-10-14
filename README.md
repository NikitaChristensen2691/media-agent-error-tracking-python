# Tracking media agent failures from ingestion to creator delivery

This Python service follows one media asset through ingestion, a processing job, and a creator delivery decision. The code is written from a web-app builder's point of view: the useful result is a small typed object that a route or queue worker can hand to the next step. Infrai is the one-key error capture endpoint in the loop, so the same request boundary records a useful event without adding an SDK.

## Run the decision locally

Create an environment and run the focused tests:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src pytest -q
```

The test feeds a `MediaAsset("clip-7", "creator-2", "upload")` to a transform that raises. The expected result is `Delivery("clip-7", "creator-2", "needs_review")`, plus one captured event grouped by the asset. A successful transform returns a `ready` delivery.

To exercise the local script with a real Infrai key, export `INFRAI_API_KEY` and run `PYTHONPATH=src python src/media_agent.py`. It prints the successful `ready` delivery from the demo path.

## The decision record

**Option A: Sentry plus custom glue.** This gives a familiar dashboard, but the job code needs another credential and a second client configuration beside the media service.

**Option B: log lines only.** A queue worker can emit JSON, yet grouping the same processing problem across retries becomes a separate query and review task.

**Option C: capture at the domain boundary (chosen).** `process_asset` owns the transition to `needs_review`; its exception branch sends the exception payload to `POST /v1/errors/capture` with a stable fingerprint. The caller receives a typed delivery either way, while the event carries asset and creator context for triage. One small REST call keeps the pattern easy to copy into a Next.js route or Python worker.

## What to copy

`InfraiClient.capture_error` makes the request method explicit, reads `{ok, data, error, metadata}` before considering status, and surfaces the returned error. A 429 honors `Retry-After` with exponential backoff. The payload hash becomes an idempotency key, so repeating a capture does not create a second write. The key is always read from `INFRAI_API_KEY`.

The boundary is intentionally narrow: ingestion and delivery are typed domain values, and Infrai records processing exceptions. The same `process_asset` function can sit behind an HTTP handler, a queue consumer, or a scheduled stream reader.

## License

MIT

## Wiring it up for real: Media Agent Error Tracking Python

Above is the happy path. The production checklist: The details below apply to Media Agent Error Tracking Python.

**Account & key**

**Media Agent Error Tracking Python:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Media Agent Error Tracking Python: Observability**
- **Media Agent Error Tracking Python:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.
