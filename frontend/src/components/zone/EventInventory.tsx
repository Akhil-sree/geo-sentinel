const RECENT_EVENTS = [
  {
    date: "2023-06-15",
    type: "Slide",
    location: "Shillong North Slopes",
    source: "NRSC Survey",
    typeColor: "#E55A2B",
  },
  {
    date: "2024-07-10",
    type: "Debris Flow",
    location: "Jowai Plateau",
    source: "Field Report",
    typeColor: "#B91C1C",
  },
  {
    date: "2024-08-22",
    type: "Rockfall",
    location: "Cherrapunji South",
    source: "Satellite Detection",
    typeColor: "#F2A623",
  },
];

export default function EventInventory() {
  return (
    <div>
      {RECENT_EVENTS.map((event, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "10px 0",
            borderBottom: i < RECENT_EVENTS.length - 1 ? "0.5px solid #F3F4F6" : "none",
          }}
        >
          <div
            style={{
              fontSize: 13,
              color: "#9CA3AF",
              fontFamily: "IBM Plex Mono",
              flexShrink: 0,
              minWidth: 80,
            }}
          >
            {event.date}
          </div>
          <span
            style={{
              fontSize: 13,
              fontWeight: 500,
              padding: "3px 10px",
              borderRadius: 4,
              background: event.typeColor + "20",
              color: event.typeColor,
              flexShrink: 0,
            }}
          >
            {event.type}
          </span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>{event.location}</div>
            <div style={{ fontSize: 12, color: "#9CA3AF", marginTop: 2 }}>{event.source}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
