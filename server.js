/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';

// ES module-friendly way to get __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
// Cloud Run provides the PORT environment variable. Default to 8080 for local development.
const port = process.env.PORT || 8080;

// Serve static files (index.html, index.css, and the compiled JS) from the root directory.
app.use(express.static(path.join(__dirname, '')));

// For a Single Page Application (SPA), all routes should lead to the index.html file.
// The client-side router (React) will then handle the specific path.
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// Listen on all network interfaces (0.0.0.0) which is required for containerized environments like Cloud Run.
app.listen(port, '0.0.0.0', () => {
  console.log(`Server is listening on port ${port}`);
});
