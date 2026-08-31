export interface GpsFix {
  lat: number;
  lng: number;
  accuracy: number;
}

export function getGps(): Promise<GpsFix> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      return reject(new Error("Geolocation unsupported"));
    }

    navigator.geolocation.getCurrentPosition(
      (p) =>
        resolve({
          lat: Number(p.coords.latitude.toFixed(5)),
          lng: Number(p.coords.longitude.toFixed(5)),
          accuracy: Math.round(p.coords.accuracy),
        }),
      (err) =>
        reject(
          new Error(
            err.code === 1 ? "Permission denied" : "Fix failed"
          )
        ),
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 30000,
      }
    );
  });
}

export const accuracyWarning = (acc: number) =>
  acc > 500
    ? `Poor GPS accuracy (±${acc}m) — confirm position before submitting`
    : null;