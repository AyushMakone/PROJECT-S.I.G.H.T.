import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useSimulation } from '../../hooks/useSimulation';
import { Telemetry, Waypoint, PriorityZone, Detection } from '../../types';
import { uploadMission } from '../../services/api';
import { Maximize2, Layers, Crosshair, Eye, Shield } from 'lucide-react';

interface MissionMapProps {
  telemetry: Telemetry;
  waypoints: Waypoint[];
  priorityZones: PriorityZone[];
  detections: Detection[];
  className?: string;
  height?: string;
  enableMissionEditing?: boolean;
}

export const MissionMap: React.FC<MissionMapProps> = ({
  telemetry,
  waypoints,
  priorityZones,
  detections,
  className = '',
  height = 'clamp(360px, 68vh, 680px)',
  enableMissionEditing = true
}) => {
  const { missionLoading, missionCard, saveMissionCard, missionSaveState } = useSimulation();
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  // Layers and markers refs
  const uavMarkerRef = useRef<L.Marker | null>(null);
  const routePolylineRef = useRef<L.Polyline | null>(null);
  const zonesLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const draftZoneLayerRef = useRef<L.Polygon | null>(null);
  const detectionsLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const waypointsLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  // UI Toggles
  const [activeTileType, setActiveTileType] = useState<'tactical' | 'street'>('tactical');
  const [showZones, setShowZones] = useState<boolean>(true);
  const [showDetections, setShowDetections] = useState<boolean>(true);
  const [trackUav, setTrackUav] = useState<boolean>(true);
  const [editMission, setEditMission] = useState<boolean>(false);
  const [editTool, setEditTool] = useState<'waypoint' | 'zone' | null>(null);
  const [draftWaypoints, setDraftWaypoints] = useState<Waypoint[]>(waypoints);
  const [draftZones, setDraftZones] = useState<PriorityZone[]>(priorityZones);
  const [draftZonePolygon, setDraftZonePolygon] = useState<[number, number][]>([]);
  const [selectedWaypointId, setSelectedWaypointId] = useState<string | null>(null);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string>('');

  const visibleWaypoints = editMission ? draftWaypoints : waypoints;
  const visibleZones = editMission ? draftZones : priorityZones;

  // Tile URL definitions
  const tileUrls = {
    tactical: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    street: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
  };

  const hasLiveUavPosition = telemetry.hasTelemetry
    && Number.isFinite(telemetry.lat)
    && Number.isFinite(telemetry.lng)
    && Math.abs(telemetry.lat) <= 90
    && Math.abs(telemetry.lng) <= 180;

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const missionCenter = priorityZones[0]?.polygon[0];
    const initialCenter: L.LatLngTuple = hasLiveUavPosition
      ? [telemetry.lat, telemetry.lng]
      : missionCenter && Number.isFinite(missionCenter[0]) && Number.isFinite(missionCenter[1])
        ? [missionCenter[0], missionCenter[1]]
        : [0, 0];

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

  useEffect(() => {
    if (!editMission) {
      setDraftWaypoints(waypoints);
      setDraftZones(priorityZones);
      setSelectedWaypointId(null);
      setSelectedZoneId(null);
    }
  }, [editMission, priorityZones, waypoints]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !editMission || !editTool) return;

    const handleMapClick = (event: L.LeafletMouseEvent) => {
      const point: [number, number] = [event.latlng.lat, event.latlng.lng];
      if (editTool === 'waypoint') {
        const waypointId = `wp-${Date.now()}`;
        setDraftWaypoints((current) => [...current, {
          id: waypointId,
          name: `WP${current.length + 1}`,
          lat: point[0],
          lng: point[1],
          altitude: 20,
          acceptanceRadius: 10,
          sequence: current.length + 1
        }]);
        setSelectedWaypointId(waypointId);
        setEditTool(null);
      } else {
        setDraftZonePolygon((current) => [...current, point]);
      }
    };

    map.on('click', handleMapClick);
    return () => { map.off('click', handleMapClick); };
  }, [editMission, editTool]);

  const finishHotZone = () => {
    if (draftZonePolygon.length < 3) {
      setSaveMessage('A hot zone needs at least 3 map points.');
      return;
    }
    const zoneId = `zone-${Date.now()}`;
    setDraftZones((current) => [...current, {
      id: zoneId,
      name: `HOT ZONE ${String(current.length + 1).padStart(2, '0')}`,
      polygon: draftZonePolygon,
      description: 'Operator-authored hot zone',
      priority: 'HIGH',
      active: true,
      fillColor: '#ef4444'
    }]);
    setSelectedZoneId(zoneId);
    setDraftZonePolygon([]);
    setEditTool(null);
  };

  const saveDraftMission = async () => {
    setSaveMessage('Saving mission...');
    try {
      await saveMissionCard({
        ...missionCard,
        waypoints: draftWaypoints,
        priorityZones: draftZones
      });
      setEditMission(false);
      setEditTool(null);
      setSaveMessage('Mission saved from backend state.');
    } catch {
      setSaveMessage('Mission save failed.');
    }
  };

  const handleUploadMission = async () => {
    const result = await uploadMission();
    setSaveMessage(result.message ?? result.status);
  };

  // Update UAV Position & Rotation
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    if (!hasLiveUavPosition) {
      if (uavMarkerRef.current) {
        uavMarkerRef.current.remove();
        uavMarkerRef.current = null;
      }
      return;
    }

    const newLatLng: L.LatLngTuple = [telemetry.lat, telemetry.lng];

    if (!uavMarkerRef.current) {
      uavMarkerRef.current = L.marker(newLatLng, {
        icon: createUavIcon(telemetry.headingDegrees ?? 0),
        zIndexOffset: 1000
      }).addTo(mapInstanceRef.current);
    }

    uavMarkerRef.current.setLatLng(newLatLng);
    uavMarkerRef.current.setIcon(createUavIcon(telemetry.headingDegrees ?? 0));
    uavMarkerRef.current.setPopupContent(`
      <div class="text-xs font-mono p-1">
        <div class="font-bold text-cyan-400">SIGHT-UAV-01</div>
        <div class="text-slate-300 mt-1">ALT (AGL): ${telemetry.relativeAltitude ?? 'N/A'}m | GS: ${telemetry.speed}m/s</div>
        <div class="text-slate-400">Heading: ${telemetry.heading} (${telemetry.headingDegrees}°)</div>
        <div class="text-emerald-400 mt-1 font-semibold">BATTERY: ${telemetry.battery}%</div>
      </div>
    `);

    if (trackUav) {
      const currentZoom = mapInstanceRef.current.getZoom();
      mapInstanceRef.current.setView(newLatLng, currentZoom || 14, { animate: true });
    }
  }, [hasLiveUavPosition, telemetry.lat, telemetry.lng, telemetry.headingDegrees, telemetry.relativeAltitude, telemetry.speed, telemetry.battery, trackUav]);

  // Update Waypoints & Route
  useEffect(() => {
    if (!mapInstanceRef.current || !waypointsLayerGroupRef.current) return;

    waypointsLayerGroupRef.current.clearLayers();

    const hasMissionRoute = visibleWaypoints.length > 0 && visibleWaypoints.some((wp) => wp.lat !== 0 || wp.lng !== 0);
    if (!hasMissionRoute) {
      if (routePolylineRef.current) {
        routePolylineRef.current.remove();
      }
      return;
    }

    const routeLatLngs: L.LatLngTuple[] = [];

    visibleWaypoints.forEach((wp, index) => {
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
              ${wp.isHome ? 'H' : `WP${index + 1}`}
            </div>
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      const marker = L.marker(latLng, { icon }).addTo(waypointsLayerGroupRef.current!);
      marker.on('click', () => {
        if (editMission) setSelectedWaypointId(wp.id);
      });
      marker.bindPopup(`
        <div class="text-xs font-mono p-1">
          <div class="font-bold text-slate-200">${wp.name}</div>
          <div class="text-slate-400 mt-0.5">Alt: ${wp.altitude}m | Seq: #${wp.sequence}</div>
        </div>
      `);
    });

    if (routePolylineRef.current) {
      routePolylineRef.current.remove();
    }

    routePolylineRef.current = L.polyline(routeLatLngs, {
      color: '#06b6d4',
      weight: 2,
      dashArray: '5, 8',
      opacity: 0.75
    }).addTo(mapInstanceRef.current);
  }, [visibleWaypoints]);

  // Update Priority Zones
  useEffect(() => {
    if (!zonesLayerGroupRef.current) return;
    zonesLayerGroupRef.current.clearLayers();

    if (!showZones) return;

    visibleZones.forEach((zone) => {
      const polygon = L.polygon(zone.polygon, {
        color: zone.fillColor || '#ef4444',
        weight: 1.5,
        fillColor: zone.fillColor || '#ef4444',
        fillOpacity: 0.15,
        dashArray: '4, 4'
      }).addTo(zonesLayerGroupRef.current!);
      polygon.on('click', () => {
        if (editMission) setSelectedZoneId(zone.id);
      });

      polygon.bindPopup(`
        <div class="text-xs font-mono p-1">
          <div class="font-bold text-red-400">${zone.name}</div>
          <div class="text-slate-300 mt-1 leading-tight">${zone.description}</div>
          <div class="text-[10px] text-amber-400 mt-1 uppercase font-semibold">PRIORITY SURVEILLANCE ZONE</div>
        </div>
      `);
    });
  }, [visibleZones, showZones]);

  useEffect(() => {
    if (draftZoneLayerRef.current) draftZoneLayerRef.current.remove();
    draftZoneLayerRef.current = null;
    if (!mapInstanceRef.current || draftZonePolygon.length < 2) return;
    draftZoneLayerRef.current = L.polygon(draftZonePolygon, {
      color: '#f59e0b',
      weight: 2,
      dashArray: '6, 4',
      fillColor: '#f59e0b',
      fillOpacity: 0.1
    }).addTo(mapInstanceRef.current);
  }, [draftZonePolygon]);

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
    if (!mapInstanceRef.current || !hasLiveUavPosition) return;
    mapInstanceRef.current.setView([telemetry.lat, telemetry.lng], mapInstanceRef.current.getZoom() || 14, { animate: true });
  };

  // Reset View to fit route
  const handleResetView = () => {
    if (!mapInstanceRef.current || visibleWaypoints.length === 0) return;
    const bounds = L.latLngBounds(visibleWaypoints.map((w) => [w.lat, w.lng] as L.LatLngTuple));
    mapInstanceRef.current.fitBounds(bounds, { padding: [40, 40], animate: true });
  };

  return (
    <div className={`w-full space-y-4 ${className}`}>
      <div className="relative w-full rounded-lg overflow-hidden border border-slate-800/90 shadow-2xl bg-[#090d14]" style={{ height }}>
      {/* Map Container */}
      <div ref={mapContainerRef} className="w-full h-full z-0" />

      {/* Floating Tactical Overlay Controls */}
      <div className="absolute top-3 left-3 z-10 flex flex-col gap-1.5 bg-[#090e17]/90 p-1.5 rounded-md border border-slate-800/90 backdrop-blur-sm shadow-xl font-mono text-xs">
        <button
          onClick={() => setTrackUav((prev) => !prev)}
          title="Toggle follow UAV mode"
          className={`flex items-center gap-1.5 px-2 py-1.5 rounded transition-colors ${
            trackUav ? 'bg-cyan-500/15 text-cyan-300' : 'hover:bg-slate-800 text-slate-300'
          }`}
        >
          <Crosshair className="w-3.5 h-3.5" />
          <span className="text-[11px]">TRACK UAV: {trackUav ? 'ON' : 'OFF'}</span>
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

      {!missionLoading && visibleZones.length === 0 && (
        <div className="absolute top-16 left-3 z-10 pointer-events-none bg-[#090e17]/90 px-2 py-1 rounded border border-slate-800 text-[10px] font-mono text-amber-300">
          NO PRIORITY ZONES CONFIGURED
        </div>
      )}

      {!visibleWaypoints.some((wp) => wp.lat !== 0 || wp.lng !== 0) && (
        <div className="absolute top-16 left-3 z-10 pointer-events-none bg-[#090e17]/90 px-2 py-1 rounded border border-slate-800 text-[10px] font-mono text-amber-300">
          MISSION ROUTE UNAVAILABLE — BACKEND MISSION HAS NO WAYPOINT DATA
        </div>
      )}

      {/* Floating Tactical Coordinates Bar at Bottom of Map */}
      <div className="absolute bottom-2.5 left-3 right-3 z-10 pointer-events-none flex items-center justify-between text-[11px] font-mono text-slate-400 bg-[#090e17]/85 px-3 py-1.5 rounded border border-slate-800/80 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <span>UAV POS: <strong className="text-cyan-400">{hasLiveUavPosition ? `${telemetry.lat.toFixed(4)}°N, ${Math.abs(telemetry.lng).toFixed(4)}°W` : 'UAV POSITION UNAVAILABLE'}</strong></span>
            <span>ALT (AGL): <strong className="text-slate-200">{telemetry.hasTelemetry ? `${telemetry.relativeAltitude ?? 'N/A'}m` : 'NO DATA'}</strong></span>
            <span>GS: <strong className="text-slate-200">{telemetry.hasTelemetry ? `${telemetry.speed}m/s` : 'NO DATA'}</strong></span>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden sm:inline">HEADING: <strong className="text-amber-400">{telemetry.hasTelemetry ? `${telemetry.heading} (${telemetry.headingDegrees}°)` : 'NO DATA'}</strong></span>
          <span className="text-emerald-400 font-semibold">GPS: {telemetry.hasTelemetry ? `${telemetry.gpsStatus} (${telemetry.gpsSatellites} SATS)` : 'NO DATA'}</span>
        </div>
      </div>
      </div>

      {enableMissionEditing && <>
      <section className="w-full rounded-lg border border-slate-800 bg-[#0b1019] p-4 shadow-xl font-mono text-xs">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-sm font-bold tracking-wider text-slate-200">MISSION EDITOR</h3>
            <p className="mt-1 text-[10px] text-slate-500">Authoritative Mission Card editing</p>
          </div>
          {!editMission && <button onClick={() => void handleUploadMission()} className="px-3 py-2 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">UPLOAD TO UAV</button>}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button onClick={() => { setEditMission((current) => !current); setEditTool(null); setSelectedWaypointId(null); setSelectedZoneId(null); setDraftZonePolygon([]); }} className="px-3 py-2 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
            {editMission ? 'EXIT EDIT' : 'EDIT MISSION'}
          </button>
          {editMission && <>
            <button onClick={() => setEditTool('waypoint')} className="px-3 py-2 rounded bg-slate-800 text-slate-200">ADD WAYPOINT</button>
            <button onClick={() => { setEditTool('zone'); setDraftZonePolygon([]); }} className="px-3 py-2 rounded bg-red-500/15 text-red-300">ADD HOT ZONE</button>
            {editTool === 'zone' && <button onClick={finishHotZone} className="px-3 py-2 rounded bg-amber-500/15 text-amber-300">FINISH ZONE</button>}
            <button onClick={() => { setDraftWaypoints([]); setDraftZones([]); setSelectedWaypointId(null); setSelectedZoneId(null); }} className="px-3 py-2 rounded bg-slate-800 text-slate-200">CLEAR</button>
            <button onClick={() => void saveDraftMission()} disabled={missionSaveState === 'SAVING'} className="px-3 py-2 rounded bg-emerald-500/15 text-emerald-300 disabled:opacity-50">SAVE MISSION</button>
          </>}
        </div>
        <div className="mt-3 text-[11px] text-slate-300">
          {saveMessage || (editMission
            ? editTool === 'waypoint' ? 'MISSION EDIT MODE · CLICK MAP TO PLACE WAYPOINT'
              : editTool === 'zone' ? 'MISSION EDIT MODE · CLICK MAP TO DRAW HOT ZONE'
              : 'MISSION EDIT MODE · SELECT A WAYPOINT OR HOT ZONE TO INSPECT'
            : 'LIVE MODE · MAP AUTHORING DISABLED')}
        </div>
      </section>

      <section className="w-full rounded-lg border border-slate-800 bg-[#0b1019] p-4 shadow-xl font-mono text-xs">
        <h3 className="text-sm font-bold tracking-wider text-slate-200">{selectedWaypointId ? 'WAYPOINT INSPECTOR' : selectedZoneId ? 'HOT ZONE INSPECTOR' : 'WAYPOINT INSPECTOR'}</h3>
        {!editMission && <p className="mt-2 text-slate-500">Enter edit mode to inspect mission elements.</p>}
        {editMission && !selectedWaypointId && !selectedZoneId && <p className="mt-2 text-slate-500">SELECT A WAYPOINT TO INSPECT</p>}
        {editMission && selectedWaypointId && (() => {
          const waypoint = draftWaypoints.find((item) => item.id === selectedWaypointId);
          if (!waypoint) return null;
          return (
            <div className="mt-3 max-w-md space-y-2 text-slate-300">
              <div className="font-bold text-cyan-300">{waypoint.name}</div>
              <div>Latitude <span className="float-right text-slate-400">{waypoint.lat.toFixed(6)}</span></div>
              <div>Longitude <span className="float-right text-slate-400">{waypoint.lng.toFixed(6)}</span></div>
              <label className="flex items-center justify-between gap-3">Altitude AGL
                <input aria-label="Waypoint altitude" type="number" min="0" value={waypoint.altitude} onChange={(event) => setDraftWaypoints((current) => current.map((item) => item.id === waypoint.id ? { ...item, altitude: Number(event.target.value) } : item))} className="w-24 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-right" />
              </label>
              <button onClick={() => { setDraftWaypoints((current) => current.filter((item) => item.id !== waypoint.id)); setSelectedWaypointId(null); }} className="mt-2 px-3 py-2 rounded border border-red-500/40 text-red-300">DELETE WAYPOINT</button>
            </div>
          );
        })()}
        {editMission && !selectedWaypointId && selectedZoneId && (() => {
          const zone = draftZones.find((item) => item.id === selectedZoneId);
          if (!zone) return null;
          return (
            <div className="mt-3 max-w-md space-y-2 text-slate-300">
              <label className="block">Name
                <input aria-label="Hot zone name" value={zone.name} onChange={(event) => setDraftZones((current) => current.map((item) => item.id === zone.id ? { ...item, name: event.target.value } : item))} className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-2 py-1" />
              </label>
              <label className="block">Priority
                <select aria-label="Hot zone priority" value={zone.priority ?? 'HIGH'} onChange={(event) => setDraftZones((current) => current.map((item) => item.id === zone.id ? { ...item, priority: event.target.value as PriorityZone['priority'] } : item))} className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-2 py-1">
                  <option>HIGH</option><option>MEDIUM</option><option>LOW</option>
                </select>
              </label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={zone.active ?? true} onChange={(event) => setDraftZones((current) => current.map((item) => item.id === zone.id ? { ...item, active: event.target.checked } : item))} /> Active</label>
              <button onClick={() => { setDraftZones((current) => current.filter((item) => item.id !== zone.id)); setSelectedZoneId(null); }} className="mt-2 px-3 py-2 rounded border border-red-500/40 text-red-300">DELETE HOT ZONE</button>
            </div>
          );
        })()}
      </section>
      </>}
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
