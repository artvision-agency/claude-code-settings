#!/bin/bash
set -euo pipefail

# image-optimize.sh — Pre-deploy image compression
# Использование: ./image-optimize.sh <input_dir> [output_dir] [max_width] [jpg_quality]
# По умолчанию: output = input/optimized, max_width=1920, quality=85

INPUT_DIR="${1:-.}"
OUTPUT_DIR="${2:-$INPUT_DIR/optimized}"
MAX_WIDTH="${3:-1920}"
JPG_QUALITY="${4:-85}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SHARP_DIR="$SCRIPT_DIR/node_modules/sharp"

if [ ! -d "$SHARP_DIR" ]; then
    echo "ERROR: sharp not installed. Run: cd $SCRIPT_DIR && npm install sharp"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "=== Image Optimization ==="
echo "Input:   $INPUT_DIR"
echo "Output:  $OUTPUT_DIR"
echo "Max:     ${MAX_WIDTH}px, Q${JPG_QUALITY}"

SCRIPT_DIR="$SCRIPT_DIR" node - "$INPUT_DIR" "$OUTPUT_DIR" "$MAX_WIDTH" "$JPG_QUALITY" << 'NODESCRIPT'
const sharp = require(require('path').join(process.env.SCRIPT_DIR, 'node_modules', 'sharp'));
const fs = require('fs');
const path = require('path');

const [,, inputDir, outputDir, maxW, jpgQ] = process.argv;
const MAX_WIDTH = parseInt(maxW);
const JPG_Q = parseInt(jpgQ);

const files = fs.readdirSync(inputDir)
    .filter(f => /\.(jpe?g|png)$/i.test(f))
    .map(f => path.join(inputDir, f));

if (!files.length) { console.log('No images found.'); process.exit(0); }

let totalOrig = 0, totalOpt = 0;

(async () => {
    for (const filePath of files) {
        const name = path.parse(filePath).name;
        const origSize = fs.statSync(filePath).size;
        totalOrig += origSize;

        const pipeline = sharp(filePath).rotate()
            .resize({ width: MAX_WIDTH, withoutEnlargement: true, fit: 'inside' });

        // JPG optimized
        const jpgOut = path.join(outputDir, name + '.jpg');
        await pipeline.clone().jpeg({ quality: JPG_Q, mozjpeg: true }).toFile(jpgOut);
        const jpgSize = fs.statSync(jpgOut).size;
        totalOpt += jpgSize;

        // WebP
        const webpOut = path.join(outputDir, name + '.webp');
        await pipeline.clone().webp({ quality: JPG_Q - 3, effort: 4 }).toFile(webpOut);

        const savePct = ((1 - jpgSize / origSize) * 100).toFixed(1);
        console.log(`  ✓ ${path.basename(filePath)}: ${(origSize/1024).toFixed(0)}KB → ${(jpgSize/1024).toFixed(0)}KB (-${savePct}%) + WebP`);
    }
    console.log(`\nTotal: ${(totalOrig/1024/1024).toFixed(1)}MB → ${(totalOpt/1024/1024).toFixed(1)}MB (-${((1-totalOpt/totalOrig)*100).toFixed(1)}%)`);
})().catch(e => { console.error(e.message); process.exit(1); });
NODESCRIPT

echo "Done."
