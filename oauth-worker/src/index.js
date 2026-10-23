export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/auth') {
      const authUrl = new URL('https://github.com/login/oauth/authorize');
      authUrl.searchParams.set('client_id', env.GITHUB_CLIENT_ID);
      authUrl.searchParams.set('redirect_uri', `${url.origin}/callback`);
      authUrl.searchParams.set('scope', 'repo,user');
      return Response.redirect(authUrl.toString(), 302);
    }

    if (url.pathname === '/callback') {
      const code = url.searchParams.get('code');
      const tokenRes = await fetch('https://github.com/login/oauth/access_token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          client_id: env.GITHUB_CLIENT_ID,
          client_secret: env.GITHUB_CLIENT_SECRET,
          code,
        }),
      });
      const { access_token, error } = await tokenRes.json();
      if (error || !access_token) {
        return new Response(`Auth error: ${error || 'no token'}`, { status: 401 });
      }

      const payload = JSON.stringify({ token: access_token, provider: 'github' }).replace(/'/g, "\\'");
      const html = `<!doctype html><html><body><script>
        (function() {
          function receiveMessage(e) {
            window.opener.postMessage('authorization:github:success:${payload}', e.origin);
            window.removeEventListener('message', receiveMessage, false);
          }
          window.addEventListener('message', receiveMessage, false);
          window.opener.postMessage('authorizing:github', '*');
        })();
      </script></body></html>`;
      return new Response(html, { headers: { 'Content-Type': 'text/html' } });
    }

    return new Response('Not found', { status: 404 });
  },
};
