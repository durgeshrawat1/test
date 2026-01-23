const fs = require('fs');
const sharp = require('sharp');

async function convert(input, output, width, height) {
  try {
    const svg = await fs.promises.readFile(input);
    await sharp(svg)
      .resize(width ? parseInt(width) : null, height ? parseInt(height) : null)
      .png({ quality: 100 })
      .toFile(output);
    console.log(`Wrote ${output}`);
  } catch (err) {
    console.error('Conversion error:', err);
    process.exitCode = 2;
  }
}

if (require.main === module) {
  const [,, input, output, width, height] = process.argv;
  if (!input || !output) {
    console.error('Usage: node convert_svg_sharp.cjs <input.svg> <output.png> [width] [height]');
    process.exit(1);
  }
  convert(input, output, width, height);
}
