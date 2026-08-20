export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 1. Route API requests to Python Backend Container
    if (url.pathname.startsWith('/api') || url.pathname === '/health') {
      if (env.PYTHON_BACKEND) {
        return await env.PYTHON_BACKEND.fetch(request);
      }
      return new Response(
        JSON.stringify({ error: "Backend Container binding unavailable" }),
        { status: 503, headers: { "content-type": "application/json" } }
      );
    }

    // 2. Route static assets & React SPA fallback
    return await env.ASSETS.fetch(request);
  }
};
