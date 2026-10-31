// Cloudflare Worker for groundline.nethren.com: serves the built frontend and
// forwards /api/* to the live coordinator backend running in a Container.
// The Anthropic key reaches the container from the ANTHROPIC_API_KEY Worker
// secret (wrangler secret put ANTHROPIC_API_KEY); it is never in the code.
import { Container, getContainer } from '@cloudflare/containers';
import { route } from './routing.js';

export class Backend extends Container {
  defaultPort = 8080;
  sleepAfter = '10m';

  constructor(ctx, env) {
    super(ctx, env);
    this.envVars = {
      ANTHROPIC_API_KEY: env.ANTHROPIC_API_KEY,
      ANTHROPIC_MODEL: env.ANTHROPIC_MODEL || 'claude-opus-5-5',
      COORDINATOR_MODE: 'live',
    };
  }
}

export default {
  // One named instance, so a run's events and fuel panel are read from the
  // same container that produced the run.
  fetch: (request, env) => route(request, env, () => getContainer(env.BACKEND, 'coordinator')),
};
