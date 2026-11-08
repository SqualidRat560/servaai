// 3D hero: a stack of coins, one coin = one month of runway, with the ServaAI tangerine
// mascot riding on top. Coins drain when an event is applied and refill with the plan.
import { Canvas, useFrame } from "@react-three/fiber";
import { ContactShadows, OrbitControls } from "@react-three/drei";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { coinCounts, MAX_COINS } from "../components/CoinStack2D.jsx";
import { C } from "../theme.js";

const COIN_H = 0.105;
const reduced = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

function Coins({ kind, from, count, color, ghost }) {
  const ref = useRef();
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const scales = useRef(new Float32Array(MAX_COINS));
  const jitter = useMemo(() => Array.from({ length: MAX_COINS }, (_, i) => [
    Math.sin(i * 12.9898) * 0.04, Math.cos(i * 78.233) * 0.04, i * 0.7]), []);

  useFrame((_, dt) => {
    const m = ref.current;
    if (!m) return;
    for (let i = 0; i < MAX_COINS; i++) {
      const slot = from + i;
      const visible = i < count ? 1 : 0;
      // stagger: higher coins move first when draining, lower first when filling
      const speed = reduced ? 1 : Math.min(1, dt * (visible ? 7 - slot * 0.12 : 4 + slot * 0.25));
      scales.current[i] += (visible - scales.current[i]) * Math.max(speed, reduced ? 1 : 0.02);
      const s = scales.current[i];
      const [jx, jz, rot] = jitter[slot] || [0, 0, 0];
      dummy.position.set(jx, slot * COIN_H + COIN_H / 2 + (1 - s) * 1.2, jz);
      dummy.rotation.set(0, rot, 0);
      dummy.scale.setScalar(Math.max(s, 0.0001));
      dummy.updateMatrix();
      m.setMatrixAt(i, dummy.matrix);
    }
    m.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={ref} args={[null, null, MAX_COINS]} key={kind}>
      <cylinderGeometry args={[0.55, 0.55, COIN_H * 0.82, 40]} />
      {ghost
        ? <meshBasicMaterial color={color} wireframe transparent opacity={0.55} />
        : <meshStandardMaterial color={color} metalness={0.05} roughness={0.85} />}
    </instancedMesh>
  );
}

function Mascot({ height }) {
  const ref = useRef();
  useFrame((state, dt) => {
    if (!ref.current) return;
    const target = height + 0.42;
    ref.current.position.y += (target - ref.current.position.y) * (reduced ? 1 : Math.min(1, dt * 3));
    if (!reduced) ref.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.6) * 0.35;
  });
  return (
    <group ref={ref} position={[0, height + 0.42, 0]}>
      <mesh castShadow>
        <icosahedronGeometry args={[0.4, 1]} />
        <meshStandardMaterial color={C.accent} roughness={0.9} flatShading />
      </mesh>
      <mesh position={[0.06, 0.43, 0]} rotation={[0, 0, -0.5]}>
        <coneGeometry args={[0.08, 0.26, 5]} />
        <meshStandardMaterial color={C.positive} flatShading />
      </mesh>
      {[-0.13, 0.13].map((x) => (
        <mesh key={x} position={[x, 0.06, 0.36]}>
          <sphereGeometry args={[0.05, 10, 10]} />
          <meshStandardMaterial color={C.ink} />
        </mesh>
      ))}
    </group>
  );
}

function Scene({ judge, realistic, backup }) {
  const { real, plan, ghost } = coinCounts(judge, realistic, backup);
  const spin = useRef();
  useFrame((_, dt) => { if (spin.current && !reduced) spin.current.rotation.y += dt * 0.12; });
  return (
    <>
      <color attach="background" args={[C.raised]} />
      <ambientLight intensity={0.9} />
      <directionalLight position={[3, 6, 4]} intensity={1.4} color={C.keyLight} castShadow />
      <directionalLight position={[-4, 2, -3]} intensity={0.5} color={C.rimLight} />
      <group ref={spin} position={[0, -1.55, 0]}>
        <Coins kind="real" from={0} count={real} color={C.accent} />
        <Coins kind="plan" from={real} count={plan} color={C.accentSoft} />
        <Coins kind="ghost" from={real + plan} count={ghost} color={C.stone} ghost />
        <Mascot height={(real + plan) * COIN_H} />
        <ContactShadows position={[0, 0, 0]} opacity={0.22} scale={5} blur={2.8} far={2} />
      </group>
      <OrbitControls enablePan={false} enableZoom={false} minPolarAngle={0.9} maxPolarAngle={1.45} />
    </>
  );
}

export default function HeroStack(props) {
  return (
    <Canvas camera={{ position: [0, 0.9, 6.6], fov: 40 }} dpr={[1, 2]} shadows
            aria-label="3D stack of coins, one per month of runway">
      <Scene {...props} />
    </Canvas>
  );
}
