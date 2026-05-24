// Node.js script to generate PNG icons via sharp or canvas
// Since we're in a minimal env, we'll create SVG icons and convert via ImageMagick if available
const fs = require('fs');
const path = require('path');

const svgTemplate = (size) => `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <rect width="${size}" height="${size}" rx="${size*0.2}" fill="#1e293b"/>
  <rect width="${size}" height="${size}" rx="${size*0.2}" fill="url(#grad)"/>
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1d4ed8"/>
      <stop offset="100%" style="stop-color:#3b82f6"/>
    </linearGradient>
  </defs>
  <text x="50%" y="56%" dominant-baseline="middle" text-anchor="middle"
        font-size="${size*0.55}" font-family="Apple Color Emoji, Segoe UI Emoji, sans-serif">💉</text>
</svg>`;

fs.writeFileSync(path.join(__dirname, 'icon-192.svg'), svgTemplate(192));
fs.writeFileSync(path.join(__dirname, 'icon-512.svg'), svgTemplate(512));
console.log('SVG icons written');
