// Vercel serverless function to proxy all /api/* requests to Railway backend
// This acts as a secure proxy that injects the secret header

export default async function handler(req, res) {
  const BACKEND_BASE = process.env.BACKEND_BASE;
  const EDGE_SECRET = process.env.EDGE_SECRET;

  // Validate environment variables
  if (!BACKEND_BASE || !EDGE_SECRET) {
    console.error('Server misconfiguration: Missing BACKEND_BASE or EDGE_SECRET');
    return res.status(500).json({ error: 'Server misconfiguration' });
  }

  // Extract the path from the query parameters
  const { path = [] } = req.query;
  let targetPath = '';
  
  if (Array.isArray(path) && path.length > 0) {
    targetPath = path.join('/');
  } else if (typeof path === 'string' && path.length > 0) {
    targetPath = path;
  }
  
  // Build the destination URL - don't add extra slash if targetPath is empty
  const queryString = req.url?.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
  const destinationUrl = targetPath 
    ? `${BACKEND_BASE}/${targetPath}${queryString}`
    : `${BACKEND_BASE}${queryString}`;
  
  // Debug logging
  console.log(`Proxying: ${req.method} ${req.url} → ${destinationUrl}`);

  try {
    // Prepare headers for the upstream request
    const upstreamHeaders = new Headers();
    
    // Copy request headers (excluding hop-by-hop headers)
    for (const [key, value] of Object.entries(req.headers)) {
      if (value === undefined) continue;
      const headerValue = Array.isArray(value) ? value.join(',') : value;
      
      // Skip hop-by-hop headers
      if (['host', 'connection', 'upgrade', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 'transfer-encoding'].includes(key.toLowerCase())) {
        continue;
      }
      
      upstreamHeaders.set(key, headerValue);
    }

    // Inject the secret authentication header
    upstreamHeaders.set('X-Edge-Auth', EDGE_SECRET);
    upstreamHeaders.set('X-Forwarded-Proto', 'https');
    upstreamHeaders.set('X-Forwarded-For', req.headers['x-forwarded-for'] || req.connection?.remoteAddress || 'unknown');

    // Prepare request body for non-GET/HEAD requests
    let body = undefined;
    if (req.method && !['GET', 'HEAD'].includes(req.method)) {
      body = JSON.stringify(req.body);
      upstreamHeaders.set('Content-Type', 'application/json');
    }

    // Make the request to the Railway backend
    const upstreamResponse = await fetch(destinationUrl, {
      method: req.method || 'GET',
      headers: upstreamHeaders,
      body: body,
      redirect: 'manual',
    });

    // Set response status
    res.status(upstreamResponse.status);

    // Copy response headers (excluding some that should be handled by Vercel)
    upstreamResponse.headers.forEach((value, key) => {
      // Skip headers that should be handled by the edge
      if (['transfer-encoding', 'connection', 'upgrade'].includes(key.toLowerCase())) {
        return;
      }
      res.setHeader(key, value);
    });

    // Stream the response body
    if (upstreamResponse.body) {
      const responseText = await upstreamResponse.text();
      res.send(responseText);
    } else {
      res.end();
    }

  } catch (error) {
    console.error('Proxy error:', error);
    res.status(502).json({ error: 'Bad Gateway: Unable to reach backend service' });
  }
}
