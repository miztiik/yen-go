/**
 * fetch-models.mjs — Download KataGo model files to public/models/.
 * Usage: node scripts/fetch-models.mjs
 */

import { mkdirSync, existsSync, createWriteStream } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import https from 'https';

const __dirname = dirname(fileURLToPath(import.meta.url));
const modelsDir = join(__dirname, '..', 'public', 'models');

const MODELS = [
  {
    name: 'kata1-b6c96-s175395328-d26788732.bin.gz',
    url: 'https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b6c96-s175395328-d26788732.bin.gz',
  },
  {
    name: 'kata1-b10c128-s114046784-d204142634.bin.gz',
    url: 'https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b10c128-s114046784-d204142634.bin.gz',
  },
];

mkdirSync(modelsDir, { recursive: true });

for (const model of MODELS) {
  const dest = join(modelsDir, model.name);
  if (existsSync(dest)) {
    console.log(`[skip] ${model.name} already exists`);
    continue;
  }

  console.log(`[download] ${model.name}...`);
  await new Promise((resolve, reject) => {
    const file = createWriteStream(dest);
    https.get(model.url, (res) => {
      if (res.statusCode === 301 || res.statusCode === 302) {
        // Follow redirect
        https.get(res.headers.location, (res2) => {
          res2.pipe(file);
          file.on('finish', () => { file.close(); resolve(); });
        }).on('error', reject);
      } else {
        res.pipe(file);
        file.on('finish', () => { file.close(); resolve(); });
      }
    }).on('error', reject);
  });
  console.log(`[done] ${model.name}`);
}

console.log('All models fetched.');
