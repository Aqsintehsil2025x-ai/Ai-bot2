# Replit Production Deployment Notes

## Important distinction
Closing the Replit editor tab is not the same as stopping a published Deployment. Do not use a workspace preview/development URL as the public production URL.

## Recommended deployment type for the current combined service
The current process starts both the Flask web server and a persistent Discord bot connection. If both must remain alive continuously, use a **Reserved VM Deployment** rather than relying on the workspace Run button or an Autoscale service that can scale down when idle.

A Reserved VM has ongoing compute charges. Check the current Replit pricing and Usage page before publishing or changing machine size. It is not a free "keep running" command, and no hosting provider guarantees zero restarts or 100% uptime.

## Deployment checklist
1. Open the Replit project and choose **Deployments / Publish**.
2. Choose **Reserved VM** for the combined always-running Flask + Discord bot process.
3. Set the run command to the repository's verified production entry point (currently expected to be `python main.py`; verify before publishing).
4. Configure the deployment's own Secrets/environment variables. Workspace Secrets are not automatically guaranteed to be present in the production Deployment.
5. Set the public domain/custom domain in Deployment settings and share that URL, not a temporary workspace preview URL.
6. Check deployment logs and the health endpoint after publishing.
7. Confirm bot reconnect behavior and persistent database/storage behavior after a deployment restart.
8. Monitor Replit Usage and configure spending limits where available.

## Architecture note
For future public XFA scale, separate the public web/API service from the persistent Discord bot worker. The XFA cloud API should not depend on a Discord bot process being alive. Use a managed database for account/integration state rather than relying on ephemeral local files.

## Do not do this
- Do not run a shell loop, fake traffic pinger, or background process to keep a development workspace awake.
- Do not assume the workspace's environment variables are the same as Deployment Secrets.
- Do not publish the current single-user XFA bearer-token endpoints as a public multi-user product.
