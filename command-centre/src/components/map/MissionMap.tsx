import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Telemetry, Waypoint, PriorityZone, Detection } from '../../types';
import { Maximize2, Layers, Crosshair, Eye, Shield } from 'lucide-react';

interface MissionMapProps {
  telemetry: Telemetry;
  waypoints: Waypoint[];
  priorityZones: PriorityZone[];
  detections: Detection[];
  className?: string;
  height?: string;
}

export const MissionMap: React.FC<MissionMapProps> = ({
  telemetry,
  waypoints,
  priorityZones,
  detections,
  className = '',
  height = '100%'
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  // Layers and markers refs
  const uavMarkerRef = useRef<L.Marker | null>(null);
  const routePolylineRef = useRef<L.Polyline | null>(null);
  const zonesLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const detectionsLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const waypointsLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  // UI Toggles
  const [activeTileType, setActiveTileType] = useState<'tactical' | 'street'>('tactical');
  const [showZones, setShowZones] = useState<boolean>(true);
  const [showDetections, setShowDetections] = useState<boolean>(true);

  // Tile URL definitions
  const tileUrls = {
    tactical: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    street: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
  };

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const initialCenter: L.LatLngTuple = [telemetry.lat || 34.0620, telemetry.lng || -117.8050];

    const map = L.map(mapContainerRef.current, {
      center: initialCenter,
      zoom: 14,
      zoomControl: false,
      attributionControl: false
    });

    tileLayerRef.current = L.tileLayer(tileUrls.tactical, {
      maxZoom: 19,
      subdomains: 'abcd'
    }).addTo(map);

    // Create Layer Groups
    zonesLayerGroupRef.current = L.layerGroup().addTo(map);
    waypointsLayerGroupRef.current = L.layerGroup().addTo(map);
    detectionsLayerGroupRef.current = L.layerGroup().addTo(map);

    // Initial UAV Marker
    const uavIcon = createUavIcon(telemetry.headingDegrees || 45);
    const uavMarker = L.marker(initialCenter, { icon: uavIcon, zIndexOffset: 1000 }).addTo(map);
    uavMarker.bindPopup(`
      <div class="text-xs font-mono p-1">
        <div class="font-bold text-cyan-400">SIGHT-UAV-01</div>
        <div class="text-slate-300 mt-1">Alt: ${telemetry.altitude}m | Spd: ${telemetry.speed}m/s</div>
        <div class="text-slate-400">Heading: ${telemetry.heading} (${telemetry.headingDegrees}°)</div>
      </div>
    `);
    uavMarkerRef.current = uavMarker;

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Tile Layer
  useEffect(() => {
    if (!mapInstanceRef.current || !tileLayerRef.current) return;
    tileLayerRef.current.setUrl(tileUrls[activeTileType]);
  }, [activeTileType]);

  // Update UAV Position & Rotation
  useEffect(() => {
    if (!uavMarkerRef.current || !telemetry.lat || !telemetry.lng) return;

    const newLatLng: L.LatLngTuple = [telemetry.lat, telemetry.lng];
    uavMarkerRef.current.setLatLng(newLatLng);
    uavMarkerRef.current.setIcon(createUavIcon(telemetry.headingDegrees || 45));

    uavMarkerRef.current.setPopupContent(`
      <div class="text-xs font-mono p-1">
        <div class="font-bold text-cyan-400">SIGHT-UAV-01</div>
        <div class="text-slate-300 mt-1">Alt: ${telemetry.altitude}m | Spd: ${telemetry.speed}m/s</div>
        <div class="text-slate-400">Heading: ${telemetry.heading} (${telemetry.headingDegrees}°)</div>
        <div class="text-emerald-400 mt-1 font-semibold">BATTERY: ${telemetry.battery}%</div>
      </div>
    `);
  }, [telemetry.lat, telemetry.lng, telemetry.headingDegrees, telemetry.altitude, telemetry.speed, telemetry.battery]);

  // Update Waypoints & Route
  useEffect(() => {
    if (!mapInstanceRef.current || !waypointsLayerGroupRef.current) return;

    waypointsLayerGroupRef.current.clearLayers();

    const routeLatLngs: L.LatLngTuple[] = [];

    waypoints.forEach((wp) => {
      const latLng: L.LatLngTuple = [wp.lat, wp.lng];
      routeLatLngs.push(latLng);

      const icon = L.divIcon({
        className: 'custom-wp-pin',
        html: `
          <div class="flex items-center justify-center -translate-x-1/2 -translate-y-1/2">
            <div class="w-6 h-6 rounded-full ${
              wp.isHome
                ? 'bg-emerald-500/20 border-2 border-emerald-400 text-emerald-300'
                : wp.isPriorityZoneAnchor
                ? 'bg-red-500/20 border-2 border-red-400 text-red-300'
                : 'bg-cyan-500/20 border-2 border-cyan-400 text-cyan-300'
            } flex items-center justify-center text-[10px] font-bold font-mono shadow-lg shadow-black/80">
              ${wp.isHome ? 'H' : wp.sequence}
            </div>
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      const marker = L.marker(latLng, { icon }).addTo(waypointsLayerGroupRef.current!);
      marker.bindPopup(`
        <div class="text-xs font-mono p-1">
          <div class="font-bold text-slate-200">${wp.name}</div>
          <div class="text-slate-400 mt-0.5">Alt: ${wp.altitude}m | Seq: #${wp.sequence}</div>
        </div>
      `);
    });

    // Draw route polyline
    if (routePolylineRef.current) {
      routePolylineRef.current.remove();
    }

    routePolylineRef.current = L.polyline(routeLatLngs, {
      color: '#06b6d4',
      weight: 2,
      dashArray: '5, 8',
      opacity: 0.75
    }).addTo(mapInstanceRef.current);
  }, [waypoints]);

  // Update Priority Zones
  useEffect(() => {
    if (!zonesLayerGroupRef.current) return;
    zonesLayerGroupRef.current.clearLayers();

    if (!showZones) return;

    priorityZones.forEach((zone) => {
      const polygon = L.polygon(zone.polygon, {
        color: zone.fillColor || '#ef4444',
        weight: 1.5,
        fillColor: zone.fillColor || '#ef4444',
        fillOpacity: 0.15,
        dashArray: '4, 4'
      }).addTo(zonesLayerGroupRef.current!);

      polygon.bindPopup(`
        <div class="text-xs font-mono p-1">
          <div class="font-bold text-red-400">${zone.name}</div>
          <div class="text-slate-300 mt-1 leading-tight">${zone.description}</div>
          <div class="text-[10px] text-amber-400 mt-1 uppercase font-semibold">PRIORITY SURVEILLANCE ZONE</div>
        </div>
      `);
    });
  }, [priorityZones, showZones]);

  // Update AI Detections Markers
  useEffect(() => {
    if (!detectionsLayerGroupRef.current) return;
    detectionsLayerGroupRef.current.clearLayers();

    if (!showDetections) return;

    detections.forEach((det) => {
      const getDetColor = (_obj: string, decision: string) => {
        if (decision === 'EVENT') return { bg: 'bg-cyan-500/30', border: 'border-cyan-400', text: 'text-cyan-300' };
        if (decision === 'RETAIN') return { bg: 'bg-amber-500/30', border: 'border-amber-400', text: 'text-amber-300' };
        return { bg: 'bg-slate-600/30', border: 'border-slate-400', text: 'text-slate-300' };
      };

      const color = getDetColor(det.object, det.governorDecision);

      const icon = L.divIcon({
        className: 'custom-det-pin',
        html: `
          <div class="relative -translate-x-1/2 -translate-y-1/2 group">
            <div class="absolute -inset-2 rounded-full ${color.bg} animate-ping opacity-50"></div>
            <div class="w-5 h-5 rounded-full ${color.bg} border-2 ${color.border} flex items-center justify-center text-[9px] font-bold font-mono ${color.text} shadow-md shadow-black">
              ${det.object[0]}
            </div>
            <div class="absolute left-6 -top-1 bg-[#090e17] border border-slate-700 text-[9px] font-mono px-1 rounded text-slate-300 whitespace-nowrap shadow">
              ${det.object} ${det.confidence}%
            </div>
          </div>
        `,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
      });

      const marker = L.marker([det.lat, det.lng], { icon }).addTo(detectionsLayerGroupRef.current!);
      marker.bindPopup(`
        <div class="text-xs font-mono p-1">
          <div class="flex items-center justify-between gap-2">
            <span class="font-bold ${color.text}">${det.object}</span>
            <span class="text-slate-400">${det.confidence}%</span>
          </div>
          <div class="text-slate-300 mt-1">${det.locationName}</div>
          <div class="text-[10px] text-slate-400 mt-0.5">Persistence: ${det.persistence} frames</div>
          <div class="mt-1 pt-1 border-t border-slate-700/80 flex items-center justify-between text-[10px]">
            <span class="text-slate-400">Governor:</span>
            <span class="font-bold ${color.text}">${det.governorDecision}</span>
          </div>
        </div>
      `);
    });
  }, [detections, showDetections]);

  // Center on UAV
  const handleCenterOnUav = () => {
    if (!mapInstanceRef.current || !telemetry.lat || !telemetry.lng) return;
    mapInstanceRef.current.setView([telemetry.lat, telemetry.lng], 15, { animate: true });
  };

  // Reset View to fit route
  const handleResetView = () => {
    if (!mapInstanceRef.current || waypoints.length === 0) return;
    const bounds = L.latLngBounds(waypoints.map((w) => [w.lat, w.lng] as L.LatLngTuple));
    mapInstanceRef.current.fitBounds(bounds, { padding: [40, 40], animate: true });
  };

  return (
    <div className={`relative w-full rounded-lg overflow-hidden border border-slate-800/90 shadow-2xl bg-[#090d14] ${className}`} style={{ height }}>
      {/* Map Container */}
      <div ref={mapContainerRef} className="w-full h-full z-0" />

      {/* Floating Tactical Overlay Controls */}
      <div className="absolute top-3 left-3 z-10 flex flex-col gap-1.5 bg-[#090e17]/90 p-1.5 rounded-md border border-slate-800/90 backdrop-blur-sm shadow-xl font-mono text-xs">
        <button
          onClick={handleCenterOnUav}
          title="Center on UAV"
          className="flex items-center gap-1.5 px-2 py-1.5 rounded hover:bg-slate-800 text-cyan-400 transition-colors"
        >
          <Crosshair className="w-3.5 h-3.5" />
          <span className="text-[11px]">TRACK UAV</span>
        </button>

        <button
          onClick={handleResetView}
          title="Fit Operational Area"
          className="flex items-center gap-1.5 px-2 py-1.5 rounded hover:bg-slate-800 text-slate-300 transition-colors"
        >
          <Maximize2 className="w-3.5 h-3.5" />
          <span className="text-[11px]">FIT ROUTE</span>
        </button>

        <div className="h-px bg-slate-800 my-0.5" />

        <button
          onClick={() => setShowZones(!showZones)}
          title="Toggle Priority Zones"
          className={`flex items-center gap-1.5 px-2 py-1 rounded transition-colors ${
            showZones ? 'text-red-400 bg-red-950/30' : 'text-slate-400 hover:bg-slate-800'
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          <span className="text-[11px]">HOT ZONES</span>
        </button>

        <button
          onClick={() => setShowDetections(!showDetections)}
          title="Toggle AI Detections"
          className={`flex items-center gap-1.5 px-2 py-1 rounded transition-colors ${
            showDetections ? 'text-cyan-400 bg-cyan-950/30' : 'text-slate-400 hover:bg-slate-800'
          }`}
        >
          <Eye className="w-3.5 h-3.5" />
          <span className="text-[11px]">AI DETECTIONS</span>
        </button>

        <button
          onClick={() => setActiveTileType(activeTileType === 'tactical' ? 'street' : 'tactical')}
          title="Switch Map Style"
          className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-slate-800 text-slate-400 transition-colors"
        >
          <Layers className="w-3.5 h-3.5" />
          <span className="text-[11px] uppercase">{activeTileType}</span>
        </button>
      </div>

      {/* Floating Tactical Coordinates Bar at Bottom of Map */}
      <div className="absolute bottom-2.5 left-3 right-3 z-10 pointer-events-none flex items-center justify-between text-[11px] font-mono text-slate-400 bg-[#090e17]/85 px-3 py-1.5 rounded border border-slate-800/80 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <span>UAV POS: <strong className="text-cyan-400">{telemetry.lat?.toFixed(4)}°N, {Math.abs(telemetry.lng || 0).toFixed(4)}°W</strong></span>
          <span>ALT: <strong className="text-slate-200">{telemetry.altitude}m</strong></span>
          <span>SPEED: <strong className="text-slate-200">{telemetry.speed}m/s</strong></span>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden sm:inline">HEADING: <strong className="text-amber-400">{telemetry.heading} ({telemetry.headingDegrees}°)</strong></span>
          <span className="text-emerald-400 font-semibold">GPS: {telemetry.gpsStatus} ({telemetry.gpsSatellites} SATS)</span>
        </div>
      </div>
    </div>
  );
};

// Helper: Custom UAV Rotatable DivIcon
function createUavIcon(headingDegrees: number) {
  return L.divIcon({
    className: 'custom-uav-marker',
    html: `
      <div style="transform: rotate(${headingDegrees}deg);" class="transition-transform duration-300 w-9 h-9 flex items-center justify-center -translate-x-1/2 -translate-y-1/2">
        <svg viewBox="0 0 36 36" class="w-9 h-9 drop-shadow-[0_0_8px_rgba(6,182,212,0.8)]" fill="none" xmlns="http://www.w3.org/2000/svg">
          <!-- Outer Radar Ring -->
          <circle cx="18" cy="18" r="16" stroke="#06b6d4" stroke-width="1.2" stroke-dasharray="2 3" opacity="0.6"/>
          
          <!-- UAV Airframe -->
          <path d="M18 4L23 16L18 13L13 16L18 4Z" fill="#22d3ee" stroke="#0891b2" stroke-width="1"/>
          <!-- Wings -->
          <path d="M7 20L18 14L29 20L27 22L18 17L9 22L7 20Z" fill="#06b6d4" opacity="0.9"/>
          <!-- Tail -->
          <path d="M15 28L18 22L21 28L18 26L15 28Z" fill="#38bdf8"/>
          <!-- Center Sensor Pod -->
          <circle cx="18" cy="16" r="2.5" fill="#f8fafc" stroke="#06b6d4" stroke-width="0.8"/>
        </svg>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18]
  });
}
