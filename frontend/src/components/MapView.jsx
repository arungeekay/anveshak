import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Renders hotspot cells as intensity-scaled circles (avoids a heatmap plugin dep).
export default function MapView({ spec, height = 320 }) {
  const center = spec?.center || [12.97, 77.59];
  const layer = (spec?.layers || [])[0] || { points: [] };
  return (
    <div style={{ height }} className="overflow-hidden rounded-lg">
      <MapContainer center={center} zoom={spec?.zoom || 11} style={{ height: "100%" }}>
        <TileLayer
          attribution="© OpenStreetMap"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {layer.points.map((p, i) => (
          <CircleMarker
            key={i}
            center={[p[0], p[1]]}
            radius={6 + (p[2] || 0) * 18}
            pathOptions={{ color: "#ef4444", fillColor: "#f59e0b", fillOpacity: 0.5 }}
          >
            <Popup>intensity {Math.round((p[2] || 0) * 100)}%</Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
