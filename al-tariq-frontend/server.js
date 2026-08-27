const http = require("http");
const fs = require("fs");
const path = require("path");

const root = __dirname;
const port = Number(process.env.PORT || 3000);
const types = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

http
  .createServer((request, response) => {
    const requested = decodeURIComponent(request.url.split("?")[0]);
    const relative = requested === "/" ? "/index.html" : requested;
    const file = path.resolve(root, `.${relative}`);

    if (!file.startsWith(root + path.sep)) {
      response.writeHead(403);
      return response.end("Forbidden");
    }

    fs.readFile(file, (error, data) => {
      if (error) {
        response.writeHead(error.code === "ENOENT" ? 404 : 500);
        return response.end(error.code === "ENOENT" ? "Not found" : "Server error");
      }
      response.writeHead(200, {
        "Content-Type": types[path.extname(file)] || "application/octet-stream",
        "Cache-Control": "no-store",
      });
      response.end(data);
    });
  })
  .listen(port, "0.0.0.0", () => {
    console.log(`Al-Tariq frontend running at http://localhost:${port}`);
  });