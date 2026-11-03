'use strict';
// Runs one bounded CPU inference, then releases all native session resources.
const fs = require('node:fs');
const path = require('node:path');
const ort = require(path.join(process.argv[2], 'node_modules', 'onnxruntime-node'));
const chunks = [];
let length = 0;
process.stdin.on('data', chunk => {
  length += chunk.length;
  if (length > 3 * 320 * 320 * 4) throw new Error('Invalid input size');
  chunks.push(chunk);
});
process.stdin.on('end', async () => {
  let session;
  try {
    const bytes = Buffer.concat(chunks);
    if (bytes.length !== 3 * 320 * 320 * 4) throw new Error('Invalid input size');
    session = await ort.InferenceSession.create(process.argv[3], {
      executionProviders: ['cpu'], intraOpNumThreads: 1, interOpNumThreads: 1,
      executionMode: 'sequential', enableCpuMemArena: false,
      extra: {session: {intra_op: {allow_spinning: '0'}, inter_op: {allow_spinning: '0'}}}
    });
    const values = new Float32Array(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
    const tensor = new ort.Tensor('float32', values, [1, 3, 320, 320]);
    const output = await session.run({[session.inputNames[0]]: tensor}, [session.outputNames[0]]);
    const mask = output[session.outputNames[0]].data;
    if (mask.length !== 320 * 320) throw new Error('Invalid mask size');
    process.stdout.write(Buffer.from(mask.buffer, mask.byteOffset, mask.byteLength));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  } finally {
    if (session) await session.release();
  }
});
