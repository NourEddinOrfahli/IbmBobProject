const http = require("http");
const fs = require("fs");
const path = require("path");

const root = __dirname;
const port = Number(process.env.PORT || 3000);
const backendHost = process.env.BACKEND_HOST || "127.0.0.1";
const backendPort = Number(process.env.BACKEND_PORT || 8000);
const types = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
};

function isBackendRequest(url) {
  return url === "/health" || url.startsWith("/api/");
}

function proxyToBackend(request, response) {
  const proxyRequest = http.request(
    {
      hostname: backendHost,
      port: backendPort,
      path: request.url,
      method: request.method,
      headers: {
        ...request.headers,
        host: `${backendHost}:${backendPort}`,
      },
    },
    (backendResponse) => {
      response.writeHead(backendResponse.statusCode || 502, backendResponse.headers);
      backendResponse.pipe(response);
    },
  );

  proxyRequest.on("error", () => {
    if (!response.headersSent) {
      response.writeHead(503, { "Content-Type": "application/json; charset=utf-8" });
      response.end(JSON.stringify({
        success: false,
        error: {
          code: "BACKEND_UNAVAILABLE",
          message: "Backend service is unavailable. Please try again.",
        },
      }));
    } else {
      response.destroy();
    }
  });

  request.pipe(proxyRequest);
}

function serveStatic(request, response) {
  let requested;
  try {
    requested = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
  } catch {
    response.writeHead(400);
    return response.end("Bad request");
  }

  const relative = requested === "/" ? "/index.html" : requested;
  const file = path.resolve(root, `.${relative}`);
  if (file !== root && !file.startsWith(root + path.sep)) {
    response.writeHead(403);
    return response.end("Forbidden");
  }

  fs.stat(file, (statError, stats) => {
    if (statError || !stats.isFile()) {
      response.writeHead(404);
      return response.end("Not found");
    }

    response.writeHead(200, {
      "Content-Type": types[path.extname(file).toLowerCase()] || "application/octet-stream",
      "Cache-Control": "no-store",
    });
    if (request.method === "HEAD") return response.end();
    fs.createReadStream(file).on("error", () => response.destroy()).pipe(response);
  });
}

http.createServer((request, response) => {
  if (isBackendRequest(request.url)) {
    return proxyToBackend(request, response);
  }
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.writeHead(405, { Allow: "GET, HEAD" });
    return response.end("Method not allowed");
  }
  return serveStatic(request, response);
}).listen(port, "0.0.0.0", () => {
  console.log(`Al-Tariq frontend running on port ${port}; proxying backend on ${backendHost}:${backendPort}`);
});