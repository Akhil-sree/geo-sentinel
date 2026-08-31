import { Marker, Popup } from "react-leaflet";
import L from "leaflet";

const pinIcon = L.divIcon({
  className: "",
  html: `<div style="width:14px;height:14px;border-radius:50%;
         background:#e0b83d;border:2px solid #0b1220;box-shadow:0 0 0 2px #e0b83d55"></div>`,
  iconSize: [14, 14], iconAnchor: [7, 7],
});

export function ReportMarker({ report }: {
  report: { id: string; lat: number; lng: number; status: string };
}) {
  return (
    <Marker position={[report.lat, report.lng]} icon={pinIcon}>
      <Popup>
        <b>Citizen report</b> · {report.status}<br />
        <span style={{ fontSize: 10 }}>Pending validation — not verified ground truth</span>
      </Popup>
    </Marker>
  );
}
