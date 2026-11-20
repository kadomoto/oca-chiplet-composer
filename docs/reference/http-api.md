# HTTP API

The browser talks to the server only through this API, so scripts can do everything the UI does. All bodies are JSON; a design is a [design file](design-file.md).

| Method and path | Body | Returns |
|---|---|---|
| `GET /api/catalog` | | chiplet templates, package technologies, defaults and the VP status |
| `POST /api/evaluate` | design | the analytic model's output: summary, issues, links, flows, dies, PHYs |
| `GET /api/sweep/params` | | the parameters a sweep can vary |
| `POST /api/sweep` | `{design, param}` | one analytic summary per value |
| `POST /api/config` | design | the [generated Harness setup](../guide/harness-setup.md) and a header per chiplet |
| `POST /api/logic/check` | `{regmap, script, model}` | errors, compiled script steps, C header and Python skeleton |
| `POST /api/runs` | `{design, engines}` | a run; `engines` is `["analytic"]` or `["analytic", "harness-vp"]` |
| `GET /api/runs` | | all runs of this server process |
| `GET /api/runs/{id}` | | a run's state, log and results |
| `GET /api/runs/{id}/events` | | server-sent events: `log` lines, then `end` |
| `POST /api/runs/{id}/cancel` | | cancels a run |
| `POST /api/export` | design | the [simulation bundle](../guide/export.md) as a zip |

```bash
curl -s -X POST localhost:8765/api/evaluate -H 'Content-Type: application/json' \
     -d @design.json | python3 -m json.tool | head
```
