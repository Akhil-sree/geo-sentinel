const ALLOWED = ["image/jpeg", "image/png", "image/webp"];
const MAX_BYTES = 8 * 1024 * 1024;

export function validateFile(f: File): string | null {
  if (!ALLOWED.includes(f.type)) return "Only JPEG/PNG/WEBP allowed";
  if (f.size > MAX_BYTES) return "File too large (>8MB)";
  return null;
}

/** Client-side downscale + JPEG recompress — cuts upload size ~10x. */
export function compressImage(file: File, maxW = 1200, quality = 0.7): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const scale = Math.min(1, maxW / img.width);
        const canvas = document.createElement("canvas");
        canvas.width = img.width * scale;
        canvas.height = img.height * scale;
        canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(
          (b) => (b ? resolve(b) : reject(new Error("compress failed"))),
          "image/jpeg", quality
        );
      };
      img.onerror = () => reject(new Error("not a readable image"));
      img.src = reader.result as string;
    };
    reader.onerror = () => reject(new Error("read failed"));
    reader.readAsDataURL(file);
  });
}
