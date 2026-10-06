# Render idle shutdown: strategy for OryxenAI

Research date: 2026-10-06. Research and recommendation only; no monitor, billing setting, deployment, or remote branch was changed.

## Recommendation

For the current Free-hosted pilot, use one external scheduled HTTPS GET to the existing process-liveness endpoint every five minutes. Use cron-job.org rather than putting a timer inside the app, running a task on the owner's PC, or adding a GitHub Actions workflow. This is a small mitigation for idle sleep, not guaranteed availability.

For a production application whose users should not encounter idle wake-up delays, use Render's smallest paid web-service instance. Paid compute does not spin down for inactivity. The current entry price is $7/month for Starter, with 512 MB RAM and 0.5 CPU. The Hobby workspace can remain free; a paid workspace subscription is not required just to purchase compute. Keep the existing combined API/worker launcher for now. [Render FAQ](https://render.com/docs/faq), [pricing](https://render.com/pricing), [instance specifications](https://render.com/docs/compute-plans).

This choice needs the operator's direction before any external setup or paid change. The existing deployment hold remains in force. Changing an instance type in the Dashboard automatically triggers a deployment, so do not make that change while release approval is pending. [Instance changes](https://render.com/docs/compute-plans).

## What is causing the delay

Render documents that a Free web service spins down after 15 minutes without inbound HTTP requests or messages on an existing WebSocket. The next request wakes it, taking about a minute. Free services can also restart at any time, independently of idle sleep. The reported delay after returning after 30 minutes matches this behavior, although this investigation did not inspect a specific shutdown incident's logs. [Free services](https://render.com/docs/free).

The read-only Render service lookup confirmed that OryxenAI currently has Free compute, one instance, the combined Python launcher, and `/health/ready` as its platform health check. Its Render origin is `https://oryxenai.onrender.com`. The service was not administratively suspended at lookup time. This does not prove that it was warm or rule out crashes. A workspace-wide inventory was unavailable without selecting a workspace, so the number of other Free services and remaining monthly hours were not verified.

In this repository, `render.yaml` selects Free. `src/oryxenai/deployment/render_web.py` runs Alembic and starts both Uvicorn and the durable worker at process startup. Frontend compilation and Docker image construction happen during deployment, not ordinary idle wake-up. When the service is asleep, its worker also cannot process queued jobs; PostgreSQL polling is not the inbound traffic that keeps a Free web service active. The durable queue preserves work, but preservation does not make a sleeping worker execute it.

Keeping the service warm addresses first-request startup latency. It does not itself accelerate upstream model inference or guarantee that generation is fast under load. Those are separate from the already implemented generation optimizations.

## What other developers do

The common workaround is an external HTTP scheduler or uptime monitor. An accepted Stack Overflow answer recommends cron-job.org; the question describes why an in-process cron stops working when the app itself is asleep. This is first-hand discussion, not a Render availability guarantee. [Discussion](https://stackoverflow.com/questions/75340700/prevent-render-server-from-sleeping).

A public implementation uses Pipedream for a morning cold start and cron-job.org during working hours. Its author reports a three-hour GitHub Actions scheduling delay and notes that cron-job.org's 30-second timeout is shorter than a cold start. Their two-service, working-hours setup is useful evidence, but adding two automation providers is unnecessary for our single-service pilot. The report's claims of guaranteed timing and GitHub having no timezone support should not be copied: primary documentation is the authority. [Implementation](https://github.com/patsarun2545/render-free-tier-wakeup).

Another public repository implements scheduled GitHub Actions requests. Its claim that a ten-minute interval keeps runtime hours well below the cap is incorrect for a service kept awake continuously: five- and ten-minute intervals both prevent the same idle shutdown and consume essentially the same active hours. [Workflow](https://github.com/repo-sumit/Survey-builder-BE/blob/f37c6ba99cdff9afc531a051dd254f3a1f002091/.github/workflows/keep-render-awake.yml).

## Options compared

| Approach | Assessment for this app |
| --- | --- |
| Render Starter web service | Supported way to eliminate inactivity-based sleep; $7/month at research time. Simplest production choice. |
| cron-job.org, HTTPS GET every five minutes | Free external scheduler with execution history and failure notifications. Best minimal Free-plan mitigation; timing is not guaranteed. |
| UptimeRobot, HTTPS GET every five minutes | Also viable, with built-in monitoring and alerts. Its current Free plan supports commercial use. Explicitly select GET for our GET-only endpoint. |
| GitHub Actions schedule | Best-effort fallback, not the main keep-alive. Runs can be delayed or dropped; schedules run on the default branch, and inactive public repositories lose schedules after 60 days. |
| Render Cron Job that pings the Free web service | Adds a separate service and at least $1/month while retaining Free-web limitations. Poor tradeoff compared with either the free scheduler or paid web compute. |
| In-process cron or local PC task | Stops when the service or PC stops. Does not solve this independently. |
| Move the frontend to a static CDN | Could make the initial shell available, but the API and worker would still sleep. Adds scope without solving agent readiness. |

Sources: [cron-job.org FAQ](https://cron-job.org/en/faq/), [UptimeRobot Free plan](https://help.uptimerobot.com/en/articles/11604710-who-should-use-uptimerobot-s-free-plan), [HTTP monitor settings](https://help.uptimerobot.com/en/articles/11358466-how-to-debug-a-monitor-showing-as-down-in-uptimerobot), [GitHub scheduling](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), [Render cron billing](https://render.com/docs/cronjobs), [Render paid availability](https://render.com/docs/faq).

## Concrete Free-plan setup to review

Create exactly one externally hosted scheduled job:

| Setting | Proposed value |
| --- | --- |
| Name | OryxenAI health check |
| Method | GET |
| URL | `https://oryxenai.onrender.com/health/live` |
| Schedule | `*/5 * * * *` — every five minutes, all day |
| Authentication / request body | None |
| Healthy application response | HTTP 200 with `{"status":"alive"}` |
| Notifications | Sustained failures, recovery, and automatic job deactivation |
| History | Save responses during setup to verify that the actual backend responds |

The route is already implemented in `src/oryxenai/api/routes/health.py`; no new endpoint or LLM call is necessary. It checks process liveness without querying PostgreSQL. Keep Render's existing `/health/ready` setting for dependency readiness. The direct Render origin avoids relying on custom-domain proxy caching. Verify that the live origin accepts the request before enabling the schedule; the proposed URL was identified from the Render API and repository, not exercised during this research.

Five minutes leaves more margin than fourteen minutes for delayed or failed checks. A cron-job.org request has a 30-second limit, so its first cold-start check can fail while waking the service; manually warm the service once before accepting the setup and inspect the next scheduled response. The provider does not guarantee punctuality, can delay troublesome jobs, and can deactivate a job after more than 25 successive failures. Enable the corresponding notification. [Scheduler limits](https://cron-job.org/en/faq/).

If UptimeRobot is preferred, set HTTPS method GET explicitly. Its HTTP monitors default to HEAD, whereas our liveness route defines GET; using the default can yield 405 and misleading downtime. Its documented timeout is configurable from 1 to 60 seconds, with 30 seconds as default. The current Free plan provides five-minute checks and explicitly allows business use; older articles describing a non-commercial-only rule are out of date. [HTTP monitor behavior](https://help.uptimerobot.com/en/articles/11358466-how-to-debug-a-monitor-showing-as-down-in-uptimerobot), [current Free-plan policy](https://help.uptimerobot.com/en/articles/11604710-who-should-use-uptimerobot-s-free-plan).

## Limits that matter

Render grants 750 Free instance hours per workspace per calendar month, shared by its running Free web services. One continuously awake service uses 720 hours in a 30-day month or 744 in a 31-day month. That fits only if other usage in the workspace leaves enough hours; there is just a six-hour margin in a 31-day month. Two continuously running Free services exceed the allowance. Shortening the request interval does not increase instance hours once the service is already continuously awake. When the allowance is exhausted, Free web services are suspended until the next month. [Runtime allowance](https://render.com/docs/free).

Do not use `/robots.txt` as the ping target: when a Free service is asleep Render answers that route itself without waking the service. Do not trigger an agent endpoint or use an ICMP network ping as a substitute for an actual application HTTP request. Claims that Render universally blocks five-minute health checks were not substantiated by the official documentation reviewed. Conversely, documented idle behavior is not a guarantee that an external ping will provide production uptime. [Render behavior and exceptions](https://render.com/docs/free).

## Acceptance before calling it resolved

1. Confirm available workspace hours and inspect any actual shutdown logs for a crash, memory failure, or administrative suspension as well as idle sleep.
2. Warm the service once and verify that GET `/health/live` returns the expected JSON, not a generic startup page.
3. After external setup is authorized, inspect at least several consecutive scheduled executions and their application responses.
4. Close the app so frontend polling cannot mask the experiment; leave it untouched for 30–40 minutes. Reopen it and compare its first API response with the prior cold start.
5. Verify `/health/ready` and worker/job progress separately. Liveness alone does not prove database readiness or successful agent output.
6. Release the already verified application changes only after explicit deployment approval. Recheck the schedule after deployment and repeat the idle-return test.

No additional broker, worker service, self-ping loop, or change to agent behavior is proposed.

## Research method

Exa searches reviewed 52 result entries across five workstreams: Render's official lifecycle and billing; first-hand developer implementations; external scheduler/monitor behavior; GitHub scheduling reliability; and adversarial validation of keep-alive claims. Follow-up searches checked current monitor terms and sought platform/community evidence. Deduplication produced 45 exact URLs, or 43 after normalizing Render `.md` mirrors and trailing slashes. These are candidate-source counts, not claims that every page was fully read or endorsed.

Relevant primary pages were fetched and checked. Official documentation controls platform behavior, pricing and scheduler limits; public repositories and Stack Overflow provide experience rather than guarantees. Vendor marketing and unsupported detection/blocking claims were excluded from the recommendation. Prices and policies can change; the links above provide their current authoritative definitions.
