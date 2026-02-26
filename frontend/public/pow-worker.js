// Web Worker for Proof-of-Work mining (Hashcash SHA-256)
// Avoids blocking the main thread during PoW computation.

self.onmessage = async function (e) {
  const { payload, difficulty } = e.data;
  const payloadBytes = new TextEncoder().encode(payload);
  const target = BigInt(1) << BigInt(256 - difficulty);
  let n = 0;

  while (true) {
    const nonce = new Uint8Array(8);
    const view = new DataView(nonce.buffer);
    view.setBigUint64(0, BigInt(n), false);

    const combined = new Uint8Array(payloadBytes.length + 8);
    combined.set(payloadBytes);
    combined.set(nonce, payloadBytes.length);

    const hashBuffer = await crypto.subtle.digest("SHA-256", combined);
    const hashArray = new Uint8Array(hashBuffer);

    let hashBigInt = BigInt(0);
    for (let i = 0; i < hashArray.length; i++) {
      hashBigInt = (hashBigInt << BigInt(8)) | BigInt(hashArray[i]);
    }

    if (hashBigInt < target) {
      const nonceHex = Array.from(nonce)
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
      const hashHex = Array.from(hashArray)
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
      self.postMessage({ nonceHex, hashHex });
      return;
    }
    n++;

    if (n % 10000 === 0) {
      self.postMessage({ progress: n });
    }
  }
};
