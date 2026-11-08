// 3D galaxy: all 4,500 customers. x = judge-formula runway, z = realistic runway,
// height = savings buffer (log scale), colour = segment. The glowing diagonal wall is
// "formula = reality"; everything far in front of it is overstated by the formula.
import { Canvas } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import { useLayoutEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { SEG_COLOR } from "../pages/Portfolio.jsx";

const AX = 30;      // months shown on each axis
const SIZE = 8;     // world units for 30 months
const pos = (p) => {
  const j = Math.min(p.judge ?? 120, AX), r = Math.min(p.realistic ?? 120, AX);
  const h = Math.log10(Math.max(p.B, 1)) / 6 * 3; // $1 .. $1M -> 0 .. 3
  return [j / AX * SIZE - SIZE / 2, h, -(r / AX * SIZE - SIZE / 2)];
};

function Points({ points, onHover, onPick }) {
  const ref = useRef();
  useLayoutEffect(() => {
    const m = ref.current, o = new THREE.Object3D(), c = new THREE.Color();
    points.forEach((p, i) => {
      o.position.set(...pos(p));
      o.updateMatrix();
      m.setMatrixAt(i, o.matrix);
      m.setColorAt(i, c.set(SEG_COLOR[p.segment]));
    });
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
  }, [points]);
  return (
    <instancedMesh ref={ref} args={[null, null, points.length]}
                   onPointerMove={(e) => { e.stopPropagation(); onHover(e.instanceId); }}
                   onPointerOut={() => onHover(null)}
                   onClick={(e) => { e.stopPropagation(); onPick(points[e.instanceId]); }}>
      <sphereGeometry args={[0.07, 8, 8]} />
      <meshBasicMaterial toneMapped={false} />
    </instancedMesh>
  );
}

function Diagonal() {
  const geo = useMemo(() => {
    const g = new THREE.PlaneGeometry(Math.SQRT2 * SIZE, 3.2);
    return g;
  }, []);
  return (
    <mesh geometry={geo} position={[0, 1.6, 0]} rotation={[0, Math.PI / 4, 0]}>
      <meshBasicMaterial color="#F28500" transparent opacity={0.07} side={THREE.DoubleSide} />
    </mesh>
  );
}

function Label({ position, children }) {
  return <Html position={position} center className="pointer-events-none whitespace-nowrap text-xs text-mist">{children}</Html>;
}

export default function Galaxy({ points }) {
  const [hover, setHover] = useState(null);
  const p = hover !== null ? points[hover] : null;
  return (
    <Canvas camera={{ position: [5.2, 4.2, 6.4], fov: 45 }} dpr={[1, 2]}>
      <color attach="background" args={["#0f2150"]} />
      <gridHelper args={[SIZE, 6, "#24407e", "#1a3168"]} />
      <Diagonal />
      <Points points={points} onHover={setHover} onPick={(pt) => { window.location.hash = `#/customer/${pt.id}`; }} />
      <Label position={[0, -0.3, SIZE / 2 + 0.6]}>Judge formula runway (0 to 30 months)</Label>
      <Label position={[-SIZE / 2 - 0.9, -0.3, 0]}>Realistic runway</Label>
      <Label position={[SIZE / 2 - 0.4, 3.4, -SIZE / 2 + 0.4]}>formula = reality</Label>
      {p && (
        <Html position={pos(p)} className="pointer-events-none">
          <div className="ml-3 rounded-lg border border-line bg-deepwater px-3 py-2 text-xs whitespace-nowrap text-frost shadow-lg">
            Account {p.id}, {p.segment.toLowerCase()}<br />
            Judge {p.judge === null ? "120+" : p.judge.toFixed(1)} vs realistic {p.realistic === null ? "120+" : p.realistic.toFixed(1)} months
          </div>
        </Html>
      )}
      <OrbitControls enablePan={false} minDistance={5} maxDistance={20} autoRotate={!hover && !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches} autoRotateSpeed={0.25} />
    </Canvas>
  );
}
