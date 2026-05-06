/**
 * Simple signup counter worker
 * Counts signups without storing email data
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    // POST /signup - count a signup
    if (request.method === 'POST' && path.endsWith('/signup')) {
      try {
        const body = await request.json();
        // We don't store the email - just count
        
        const countKey = `signup_count_${env.idea_id || 'default'}`;
        const current = await env.SIGNUPS.get(countKey) || '0';
        const newCount = parseInt(current) + 1;
        
        await env.SIGNUPS.put(countKey, newCount.toString());
        
        return new Response(JSON.stringify({
          success: true,
          count: newCount
        }), {
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        });
      } catch (e) {
        return new Response(JSON.stringify({ success: false, error: e.message }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    // GET /count - get current count
    if (request.method === 'GET' && path.endsWith('/count')) {
      const countKey = `signup_count_${env.idea_id || 'default'}`;
      const count = await env.SIGNUPS.get(countKey) || '0';
      
      return new Response(JSON.stringify({
        count: parseInt(count)
      }), {
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    return new Response('OK');
  },
};