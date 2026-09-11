// Verifies the open-DEM terrain source behind the 3D view (stdlib only).
// Fetches the Terrarium tile over Sohra (Cherrapunji), decodes the PNG with
// node:zlib, and asserts the elevation is real Meghalaya-plateau terrain.
import { inflateSync } from "node:zlib";

const Z = 12;
// Sohra / Cherrapunji plateau (~1400 m). Plausible decoded range for this tile.
const LAT = 25.28;
const LON = 91.7;
const MIN_M = 300;
const MAX_M = 2500;

const n = 2 ** Z;
const tx = Math.floor(((LON + 180) / 360) * n);
const latRad = (LAT * Math.PI) / 180;
const ty = Math.floor((((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n));
const url = `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/${Z}/${tx}/${ty}.png`;

const res = await fetch(url);
if (!res.ok) throw new Error(`tile HTTP ${res.status}`);
const buf = Buffer.from(await res.arrayBuffer());

// --- minimal PNG decoder (8-bit RGB, non-interlaced) ---
if (buf.readUInt32BE(0) !== 0x89504e47) throw new Error("not a PNG");
let pos = 8;
let width = 0;
let height = 0;
const idat = [];
while (pos < buf.length) {
  const len = buf.readUInt32BE(pos);
  const type = buf.toString("ascii", pos + 4, pos + 8);
  const data = buf.subarray(pos + 8, pos + 8 + len);
  if (type === "IHDR") {
    width = data.readUInt32BE(0);
    height = data.readUInt32BE(4);
    if (data[8] !== 8 || data[9] !== 2 || data[12] !== 0) {
      throw new Error(`unexpected PNG format depth=${data[8]} type=${data[9]}`);
    }
  } else if (type === "IDAT") {
    idat.push(data);
  } else if (type === "IEND") {
    break;
  }
  pos += 12 + len;
}
const raw = inflateSync(Buffer.concat(idat));
const bpp = 3;
const stride = width * bpp;
const img = Buffer.alloc(height * stride);
for (let y = 0; y < height; y++) {
  const f = raw[y * (stride + 1)];
  const row = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1));
  const prev = y === 0 ? Buffer.alloc(stride) : img.subarray((y - 1) * stride, y * stride);
  const out = img.subarray(y * stride, (y + 1) * stride);
  for (let x = 0; x < stride; x++) {
    const a = x >= bpp ? out[x - bpp] : 0;
    const b = prev[x];
    const c = x >= bpp ? prev[x - bpp] : 0;
    let v = row[x];
    if (f === 1) v += a;
    else if (f === 2) v += b;
    else if (f === 3) v += (a + b) >> 1;
    else if (f === 4) {
      const p = a + b - c;
      const pa = Math.abs(p - a);
      const pb = Math.abs(p - b);
      const pc = Math.abs(p - c);
      v += pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
    }
    out[x] = v & 0xff;
  }
}

const elev = (x, y) => {
  const o = (y * width + x) * bpp;
  return img[o] * 256 + img[o + 1] + img[o + 2] / 256 - 32768;
};
// Pixel nearest to Sohra within this tile.
const slippyX = ((LON + 180) / 360) * n;
const slippyY = ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n;
const px = Math.floor((slippyX - tx) * width);
const py = Math.floor((slippyY - ty) * height);
const center = elev(px, py);
let min = Infinity;
let max = -Infinity;
for (let y = 0; y < height; y += 4) {
  for (let x = 0; x < width; x += 4) {
    const h = elev(x, y);
    if (h < min) min = h;
    if (h < 9000 && h > max) max = h; // ignore void-fill spikes
  }
}
console.log(`tile z${Z}/${tx}/${ty} (${width}x${height})`);
console.log(`Sohra pixel elevation: ${center.toFixed(1)} m`);
console.log(`tile relief range: ${min.toFixed(0)} .. ${max.toFixed(0)} m`);
if (!(center > MIN_M && center < MAX_M)) {
  throw new Error(`elevation ${center.toFixed(1)} m outside expected Meghalaya range`);
}
console.log("REAL ELEVATION OK: open DEM terrain verified, no API key used");
