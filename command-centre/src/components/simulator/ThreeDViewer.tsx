import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Telemetry, PriorityZone } from '../../types';
import { Compass, Eye, ShieldAlert, Navigation } from 'lucide-react';

interface ThreeDViewerProps {
  telemetry: Telemetry;
  priorityZones?: PriorityZone[];
  onManualControl?: (vx: number, vy: number, vz: number, yawRate: number) => void;
  className?: string;
  height?: string;
}

export const ThreeDViewer: React.FC<ThreeDViewerProps> = ({
  telemetry,
  priorityZones = [],
  onManualControl,
  className = '',
  height = '480px'
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const droneGroupRef = useRef<THREE.Group | null>(null);
  const rotorsRef = useRef<THREE.Mesh[]>([]);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const referenceRef = useRef<{ lat: number; lng: number } | null>(null);
  const telemetryArmedRef = useRef<boolean>(false);

  const [cameraMode, setCameraMode] = useState<'chase' | 'orbit' | 'gimbal'>('chase');
  const [controlActive, setControlActive] = useState<boolean>(false);

  // Initialize Three.js Scene
  useEffect(() => {
    if (!mountRef.current) return;
    const width = mountRef.current.clientWidth;
    const heightPx = mountRef.current.clientHeight || 480;

    // 1. Scene & Camera
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x06090f);
    scene.fog = new THREE.FogExp2(0x06090f, 0.0035);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(55, width / heightPx, 0.5, 1500);
    camera.position.set(0, 30, 45);
    cameraRef.current = camera;

    // 2. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'low-power' });
    renderer.setSize(width, heightPx);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.shadowMap.enabled = false; // Disable heavy shadows for 8GB laptop performance
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 3. Lighting
    const ambientLight = new THREE.AmbientLight(0xddeeff, 0.9);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x00e5ff, 1.2);
    dirLight.position.set(50, 100, 30);
    scene.add(dirLight);

    const redLight = new THREE.PointLight(0xff3366, 1.0, 100);
    redLight.position.set(-20, 15, -20);
    scene.add(redLight);

    // 4. Tactical Proving Ground Terrain (Grid & Runway)
    const gridHelper = new THREE.GridHelper(400, 80, 0x00f3ff, 0x112233);
    gridHelper.position.y = 0;
    scene.add(gridHelper);

    // Ground plane
    const groundGeo = new THREE.PlaneGeometry(400, 400);
    const groundMat = new THREE.MeshBasicMaterial({ color: 0x070c14, depthWrite: false });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.05;
    scene.add(ground);

    // Perimeter / Runway line
    const runwayGeo = new THREE.PlaneGeometry(24, 300);
    const runwayMat = new THREE.MeshBasicMaterial({ color: 0x0c1524, depthWrite: false });
    const runway = new THREE.Mesh(runwayGeo, runwayMat);
    runway.rotation.x = -Math.PI / 2;
    runway.position.set(0, 0.01, 0);
    scene.add(runway);

    // Priority Zone Cylinders
    priorityZones.forEach((_, idx) => {
      const zoneGeo = new THREE.CylinderGeometry(35, 35, 60, 24, 1, true);
      const zoneMat = new THREE.MeshBasicMaterial({
        color: idx === 0 ? 0xff3344 : 0xffaa00,
        transparent: true,
        opacity: 0.18,
        wireframe: true
      });
      const zoneMesh = new THREE.Mesh(zoneGeo, zoneMat);
      zoneMesh.position.set(idx === 0 ? 40 : -45, 30, idx === 0 ? -60 : 40);
      scene.add(zoneMesh);
    });

    // 5. 3D UAV Drone Model
    const drone = new THREE.Group();
    droneGroupRef.current = drone;

    // Fuselage chassis
    const bodyGeo = new THREE.BoxGeometry(3.2, 0.9, 4.4);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x18202c,
      roughness: 0.3,
      metalness: 0.8
    });
    const bodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
    drone.add(bodyMesh);

    // Glowing SIGHT Beacon LED (Top)
    const ledGeo = new THREE.SphereGeometry(0.35, 12, 12);
    const ledMat = new THREE.MeshBasicMaterial({ color: 0x00f3ff });
    const ledMesh = new THREE.Mesh(ledGeo, ledMat);
    ledMesh.position.set(0, 0.65, 0);
    drone.add(ledMesh);

    // Gimbal Camera (Front bottom)
    const gimbalGeo = new THREE.SphereGeometry(0.55, 12, 12);
    const gimbalMat = new THREE.MeshStandardMaterial({ color: 0x0a1018, metalness: 0.9 });
    const gimbalMesh = new THREE.Mesh(gimbalGeo, gimbalMat);
    gimbalMesh.position.set(0, -0.45, 1.8);
    drone.add(gimbalMesh);

    // Camera Frustum Visualizer
    const frustumGeo = new THREE.ConeGeometry(8, 18, 4, 1, true);
    const frustumMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      wireframe: true,
      transparent: true,
      opacity: 0.25
    });
    const frustum = new THREE.Mesh(frustumGeo, frustumMat);
    frustum.rotation.x = Math.PI / 2.3;
    frustum.position.set(0, -9, 8);
    drone.add(frustum);

    // 4 Quadrotor Arms & Rotors
    const armMat = new THREE.MeshStandardMaterial({ color: 0x0d141e, roughness: 0.4 });
    const rotorMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.85 });
    const armPositions = [
      [3.0, 0.1, 3.0],
      [-3.0, 0.1, 3.0],
      [3.0, 0.1, -3.0],
      [-3.0, 0.1, -3.0]
    ];

    rotorsRef.current = [];

    armPositions.forEach(([x, y, z]) => {
      // Carbon arm tube
      const armGeo = new THREE.CylinderGeometry(0.2, 0.2, Math.hypot(x, z), 8);
      const arm = new THREE.Mesh(armGeo, armMat);
      arm.position.set(x / 2, y, z / 2);
      arm.rotation.z = Math.atan2(x, z);
      arm.rotation.x = Math.PI / 2;
      drone.add(arm);

      // Motor mount
      const motorGeo = new THREE.CylinderGeometry(0.5, 0.5, 0.6, 12);
      const motor = new THREE.Mesh(motorGeo, bodyMat);
      motor.position.set(x, y + 0.2, z);
      drone.add(motor);

      // Propeller Rotor Disk
      const rotorGeo = new THREE.CylinderGeometry(1.6, 1.6, 0.05, 16);
      const rotor = new THREE.Mesh(rotorGeo, rotorMat);
      rotor.position.set(x, y + 0.55, z);
      drone.add(rotor);
      rotorsRef.current.push(rotor);
    });

    scene.add(drone);

    // Resize Handler
    const handleResize = () => {
      if (!mountRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight || 480;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      // Spin rotors when armed
      if (telemetryArmedRef.current) {
        rotorsRef.current.forEach((rotor, i) => {
          rotor.rotation.y += (i % 2 === 0 ? 0.45 : -0.45);
        });
      }

      renderer.render(scene, camera);
    };
    animate();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
      renderer.dispose();
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
    };
  }, []);

  useEffect(() => {
    telemetryArmedRef.current = telemetry.hasTelemetry === true && telemetry.isArmed === true;
  }, [telemetry.hasTelemetry, telemetry.isArmed]);

  const liveTelemetryMapped = Boolean(telemetry.hasTelemetry && Number.isFinite(telemetry.lat) && Number.isFinite(telemetry.lng));

  // Update Drone 3D Position & Attitude from Genuine Telemetry
  useEffect(() => {
    if (!droneGroupRef.current || !cameraRef.current || !liveTelemetryMapped) return;
    const drone = droneGroupRef.current;
    const camera = cameraRef.current;

    if (!referenceRef.current) {
      referenceRef.current = { lat: telemetry.lat, lng: telemetry.lng };
    }

    const reference = referenceRef.current;
    const northMeters = (telemetry.lat - reference.lat) * 111139;
    const eastMeters = (telemetry.lng - reference.lng) * 111139 * Math.cos(THREE.MathUtils.degToRad(reference.lat));
    drone.position.x = eastMeters * 0.1;
    drone.position.z = -northMeters * 0.1;

    // Real ArduPilot values mapped to the 3D model without inventing flight behavior.
    const mappedAltitude = typeof telemetry.relativeAltitude === 'number' ? telemetry.relativeAltitude : telemetry.altitude;
    const targetY = Math.max(0.6, mappedAltitude * 0.5);
    drone.position.y = THREE.MathUtils.lerp(drone.position.y, targetY, 0.15);

    const rollRad = THREE.MathUtils.degToRad(telemetry.roll || 0);
    const pitchRad = THREE.MathUtils.degToRad(-(telemetry.pitch || 0));
    const yawDeg = typeof telemetry.headingDegrees === 'number' ? telemetry.headingDegrees : (typeof telemetry.yaw === 'number' ? telemetry.yaw : 0);
    const yawRad = THREE.MathUtils.degToRad(-yawDeg);

    drone.rotation.order = 'YXZ';
    drone.rotation.y = yawRad;
    drone.rotation.z = rollRad;
    drone.rotation.x = pitchRad;

    if (cameraMode === 'chase') {
      const offset = new THREE.Vector3(0, 12, -28).applyAxisAngle(new THREE.Vector3(0, 1, 0), yawRad);
      camera.position.lerp(drone.position.clone().add(offset), 0.1);
      camera.lookAt(drone.position.clone().add(new THREE.Vector3(0, 2, 0)));
    } else if (cameraMode === 'gimbal') {
      camera.position.set(drone.position.x, drone.position.y - 0.5, drone.position.z);
      camera.rotation.set(-Math.PI / 2.3, 0, yawRad);
    } else {
      camera.lookAt(drone.position);
    }
  }, [telemetry, cameraMode, liveTelemetryMapped]);

  // Keyboard Flight Controls
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!controlActive || !onManualControl) return;
      let vx = 0, vy = 0, vz = 0, yaw = 0;
      switch (e.key.toLowerCase()) {
        case 'w': vx = 4.0; break;
        case 's': vx = -4.0; break;
        case 'a': vy = -4.0; break;
        case 'd': vy = 4.0; break;
        case 'q': yaw = -25.0; break;
        case 'e': yaw = 25.0; break;
        case 'arrowup': vz = -2.5; break; // Climb
        case 'arrowdown': vz = 2.5; break; // Descend
        default: return;
      }
      e.preventDefault();
      onManualControl(vx, vy, vz, yaw);
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [controlActive, onManualControl]);

  return (
    <div className={`relative w-full rounded-xl overflow-hidden border border-slate-800 bg-[#06090f] ${className}`}>
      {/* 3D WebGL Canvas */}
      <div ref={mountRef} style={{ width: '100%', height }} />

      {!liveTelemetryMapped && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-[#06090f]/85 text-cyan-300 font-mono text-xs tracking-[0.2em]">
          3D VIEW — LIVE TELEMETRY NOT YET MAPPED
        </div>
      )}

      {/* Top HUD Overlay */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none font-mono text-xs">
        <div className="flex items-center gap-2 bg-[#090e18]/85 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-800 pointer-events-auto shadow-lg">
          <Navigation className="w-3.5 h-3.5 text-cyan-400" />
          <span className="font-bold text-slate-200">LIVE ARDUPILOT 3D VIEW</span>
          <span className="text-slate-600">|</span>
          <span className="text-cyan-400">{telemetry.hasTelemetry ? telemetry.flightMode : 'NO DATA'}</span>
          <span className="text-slate-600">|</span>
          <span className={telemetry.hasTelemetry && telemetry.isArmed ? 'text-emerald-400 font-bold' : 'text-amber-400'}>
            {telemetry.hasTelemetry ? (telemetry.isArmed ? 'ARMED' : 'DISARMED') : 'ARMED: NO DATA'}
          </span>
        </div>

        {/* View mode toggle */}
        <div className="flex items-center gap-1.5 bg-[#090e18]/85 backdrop-blur-md p-1 rounded-lg border border-slate-800 pointer-events-auto">
          <button
            onClick={() => setCameraMode('chase')}
            className={`px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
              cameraMode === 'chase' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Chase Cam
          </button>
          <button
            onClick={() => setCameraMode('gimbal')}
            className={`px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
              cameraMode === 'gimbal' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Gimbal Down
          </button>
          <button
            onClick={() => setCameraMode('orbit')}
            className={`px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
              cameraMode === 'orbit' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Tactical Orbit
          </button>
        </div>
      </div>

      {/* Bottom HUD Overlay: Telemetry & Manual Flight Keys */}
      <div className="absolute bottom-3 left-3 right-3 flex flex-col md:flex-row items-start md:items-end justify-between gap-2 pointer-events-none font-mono text-xs">
        {/* Real Attitude Readout */}
        <div className="bg-[#090e18]/85 backdrop-blur-md px-3 py-2 rounded-lg border border-slate-800 space-y-1 text-[11px]">
          <div className="flex items-center gap-4 text-slate-300">
            <span>ROLL: <strong className="text-cyan-400">{telemetry.hasTelemetry ? `${telemetry.roll}°` : '---'}</strong></span>
            <span>PITCH: <strong className="text-cyan-400">{telemetry.hasTelemetry ? `${telemetry.pitch}°` : '---'}</strong></span>
            <span>YAW: <strong className="text-cyan-400">{telemetry.hasTelemetry ? `${telemetry.headingDegrees}° (${telemetry.heading})` : '---'}</strong></span>
          </div>
          <div className="flex items-center gap-4 text-slate-400">
            <span>ALT: <strong className="text-slate-200">{telemetry.hasTelemetry ? `${telemetry.altitude}m` : '---'}</strong></span>
            <span>SPEED: <strong className="text-slate-200">{telemetry.hasTelemetry ? `${telemetry.speed}m/s` : '---'}</strong></span>
            <span>BATTERY: <strong className="text-emerald-400">{telemetry.hasTelemetry ? `${telemetry.battery}%` : '---'}</strong></span>
          </div>
        </div>

        {/* Flight Control Keybinds Badge */}
        <div className="bg-[#090e18]/85 backdrop-blur-md px-3 py-2 rounded-lg border border-slate-800 pointer-events-auto text-[11px] flex items-center gap-3">
          <button
            onClick={() => setControlActive(!controlActive)}
            className={`px-3 py-1 rounded font-bold transition-colors ${
              controlActive
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {controlActive ? 'KEYBOARD FLIGHT: ACTIVE' : 'ENABLE KEYBOARD FLIGHT'}
          </button>
          {controlActive && (
            <span className="text-slate-400 text-[10px] hidden md:inline">
              [W/S] Pitch | [A/D] Roll | [Q/E] Yaw | [↑/↓] Altitude
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
