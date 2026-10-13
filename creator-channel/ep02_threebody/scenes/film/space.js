// 宇宙层：three.js 场景 + 电影后期链。每帧由镜头函数给出一份 cfg，draw(cfg) 返回渲染好的 WebGL 画布。
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { Line2 } from 'three/addons/lines/Line2.js';
import { LineGeometry } from 'three/addons/lines/LineGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';

export const NOISE = `
vec3 mod289(vec3 x){return x-floor(x*(1./289.))*289.;}
vec4 mod289(vec4 x){return x-floor(x*(1./289.))*289.;}
vec4 permute(vec4 x){return mod289(((x*34.)+1.)*x);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){
  const vec2 C=vec2(1./6.,1./3.);const vec4 D=vec4(0.,.5,1.,2.);
  vec3 i=floor(v+dot(v,C.yyy));vec3 x0=v-i+dot(i,C.xxx);
  vec3 g=step(x0.yzx,x0.xyz);vec3 l=1.-g;vec3 i1=min(g.xyz,l.zxy);vec3 i2=max(g.xyz,l.zxy);
  vec3 x1=x0-i1+C.xxx;vec3 x2=x0-i2+C.yyy;vec3 x3=x0-D.yyy;i=mod289(i);
  vec4 p=permute(permute(permute(i.z+vec4(0.,i1.z,i2.z,1.))+i.y+vec4(0.,i1.y,i2.y,1.))+i.x+vec4(0.,i1.x,i2.x,1.));
  float n_=.142857142857;vec3 ns=n_*D.wyz-D.xzx;vec4 j=p-49.*floor(p*ns.z*ns.z);
  vec4 x_=floor(j*ns.z);vec4 y_=floor(j-7.*x_);vec4 x=x_*ns.x+ns.yyyy;vec4 y=y_*ns.x+ns.yyyy;vec4 h=1.-abs(x)-abs(y);
  vec4 b0=vec4(x.xy,y.xy);vec4 b1=vec4(x.zw,y.zw);vec4 s0=floor(b0)*2.+1.;vec4 s1=floor(b1)*2.+1.;vec4 sh=-step(h,vec4(0.));
  vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
  vec3 p0=vec3(a0.xy,h.x);vec3 p1=vec3(a0.zw,h.y);vec3 p2=vec3(a1.xy,h.z);vec3 p3=vec3(a1.zw,h.w);
  vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
  vec4 m=max(.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.);m=m*m;
  return 42.*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));}
float fbm(vec3 p){float s=0.,a=.5;for(int i=0;i<6;i++){s+=a*snoise(p);p*=2.03;a*=.5;}return s;}
`;

const N_STAR = 4, N_PLANET = 4, N_TRAIL = 10, TRAIL_CAP = 8192, N_THIN = 112, THIN_CAP = 2048;

export function createSpace(W, H) {
  const canvas = document.createElement('canvas');
  canvas.width = W; canvas.height = H;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, alpha: false });
  renderer.setPixelRatio(1);
  renderer.setSize(W, H, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, W / H, 0.002, 9000);
  const U = { uS: { value: [0, 1, 2, 3].map(() => new THREE.Vector3(999, 999, 999)) }, uC: { value: [0, 1, 2, 3].map(() => new THREE.Color(0)) }, uT: { value: 0 } };

  // 天空：星云球 + 星点，跟着镜头走，所以任何尺度下都在无穷远
  const sky = new THREE.Group();
  {
    const mat = new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, uniforms: { uA: { value: 1 } },
      vertexShader: `varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
      fragmentShader: NOISE + `
        uniform float uA; varying vec3 vP;
        void main(){
          vec3 n = vP;
          vec3 axis = normalize(vec3(0.5, 1.0, -0.15));
          float band = exp(-pow(dot(n, axis) * 2.6, 2.0));
          float cloud = fbm(n * 2.6) * 0.5 + 0.5;
          float dust = smoothstep(0.42, 0.75, fbm(n * 5.5 + 4.0) * 0.5 + 0.5);
          vec3 col = vec3(0.004, 0.006, 0.012);
          col += band * pow(cloud, 1.6) * vec3(0.06, 0.055, 0.075) * (1.0 - 0.85 * dust);
          col += band * pow(cloud, 4.0) * vec3(0.10, 0.045, 0.03) * 0.9;
          col += pow(max(0.0, fbm(n * 1.7 + 9.0)), 2.2) * vec3(0.0, 0.03, 0.06);
          gl_FragColor = vec4(col * uA, 1.0);
        }`,
    });
    sky.add(new THREE.Mesh(new THREE.SphereGeometry(4000, 64, 32), mat));
    sky.userData.mat = mat;
    let s = 99;
    const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    const n = 9000, pos = new Float32Array(n * 3), col = new Float32Array(n * 3);
    const axis = new THREE.Vector3(0.5, 1.0, -0.15).normalize();
    for (let i = 0; i < n; i++) {
      let v;
      do { const u = r() * 2 - 1, th = r() * Math.PI * 2, q = Math.sqrt(1 - u * u); v = new THREE.Vector3(q * Math.cos(th), u, q * Math.sin(th)); }
      while (r() > 0.25 + 0.75 * Math.exp(-Math.pow(v.dot(axis) * 2.6, 2)));
      pos.set(v.multiplyScalar(3000).toArray(), i * 3);
      const b = 0.18 + Math.pow(r(), 10) * 3.0, t = r();
      const c = t < 0.15 ? [1, 0.72, 0.5] : t < 0.3 ? [0.65, 0.8, 1] : [1, 0.96, 0.9];
      col.set(c.map((x) => x * b), i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const pm = new THREE.PointsMaterial({ size: 1.5, sizeAttenuation: false, vertexColors: true, depthWrite: false, transparent: true });
    sky.add(new THREE.Points(g, pm));
    sky.userData.pm = pm;
  }
  scene.add(sky);

  // 尘埃：离哪颗星近就染哪颗的颜色
  const dust = (() => {
    let s = 5;
    const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    const n = 14000, pos = new Float32Array(n * 3), sz = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const R = 0.4 + Math.pow(r(), 0.7) * 9, th = r() * Math.PI * 2;
      pos.set([R * Math.cos(th), (r() - 0.5) * (0.25 + R * 0.18), R * Math.sin(th)], i * 3);
      sz[i] = 0.5 + r() * 1.5;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('size', new THREE.BufferAttribute(sz, 1));
    const mat = new THREE.ShaderMaterial({
      uniforms: { ...U, uA: { value: 1 }, uK: { value: 1 } }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      vertexShader: `attribute float size; uniform vec3 uS[4]; uniform vec3 uC[4]; uniform float uK; varying vec3 vCol;
        void main(){
          vec4 w = modelMatrix * vec4(position, 1.0);
          vec3 c = vec3(0.0);
          for (int i = 0; i < 4; i++) { float d = distance(w.xyz, uS[i]) / uK; c += uC[i] * 0.05 / (d * d + 0.08); }
          vCol = min(c, vec3(1.2)) * 0.5;
          vec4 mv = viewMatrix * w;
          gl_PointSize = size * clamp(6.0 * uK / -mv.z, 0.6, 3.5);
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: `uniform float uA; varying vec3 vCol; void main(){ float d = length(gl_PointCoord - 0.5); gl_FragColor = vec4(vCol * uA * smoothstep(0.5, 0.0, d), 1.0); }`,
    });
    const p = new THREE.Points(g, mat);
    p.frustumCulled = false;
    scene.add(p);
    return p;
  })();

  // 恒星
  const glowTex = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 512;
    const g = c.getContext('2d'), gr = g.createRadialGradient(256, 256, 0, 256, 256, 256);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.05, 'rgba(255,255,255,0.6)');
    gr.addColorStop(0.15, 'rgba(255,255,255,0.18)'); gr.addColorStop(0.45, 'rgba(255,255,255,0.04)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 512, 512);
    return new THREE.CanvasTexture(c);
  })();
  const stars = [];
  for (let j = 0; j < N_STAR; j++) {
    const mat = new THREE.ShaderMaterial({
      uniforms: { uT: U.uT, uCol: { value: new THREE.Color() }, uSeed: { value: j * 17.3 }, uA: { value: 1 } },
      transparent: true,
      vertexShader: `varying vec3 vN; varying vec3 vP; varying vec3 vV;
        void main(){ vP = position; vN = normalize(normalMatrix*normal); vec4 mv = modelViewMatrix*vec4(position,1.); vV = normalize(-mv.xyz); gl_Position = projectionMatrix*mv; }`,
      fragmentShader: NOISE + `
        uniform float uT; uniform vec3 uCol; uniform float uSeed; uniform float uA;
        varying vec3 vN; varying vec3 vP; varying vec3 vV;
        void main(){
          vec3 p = normalize(vP);
          float g = fbm(p * 5.0 + vec3(uSeed, uT * 0.2, -uT * 0.12));
          float mu = clamp(dot(vN, vV), 0.0, 1.0);
          vec3 core = mix(uCol, vec3(1.0), 0.65);
          vec3 col = mix(uCol * 1.2, core * 2.2, smoothstep(-0.4, 0.6, g)) * (0.45 + 0.75 * pow(mu, 0.6));
          gl_FragColor = vec4(col * 2.2, uA);
        }`,
    });
    const body = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), mat);
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
    scene.add(glow, body);
    stars.push({ body, glow, mat });
  }

  // 行星：被一颗恒星照亮，表面纹理按类型生成
  const planets = [];
  for (let j = 0; j < N_PLANET; j++) {
    const mat = new THREE.ShaderMaterial({
      uniforms: { uL: { value: new THREE.Vector3() }, uLC: { value: new THREE.Color(1, 1, 1) }, uType: { value: 0 }, uA: { value: 1 }, uSeed: { value: j * 3.1 }, uRot: { value: 0 }, uTint: { value: new THREE.Color(1, 1, 1) } },
      transparent: true, depthWrite: true,
      vertexShader: `varying vec3 vW; varying vec3 vN; varying vec3 vO;
        void main(){ vO = position; vec4 w = modelMatrix*vec4(position,1.); vW = w.xyz; vN = normalize(mat3(modelMatrix)*normal); gl_Position = projectionMatrix*viewMatrix*w; }`,
      fragmentShader: NOISE + `
        uniform vec3 uL; uniform vec3 uLC; uniform float uType; uniform float uA; uniform float uSeed; uniform float uRot; uniform vec3 uTint;
        varying vec3 vW; varying vec3 vN; varying vec3 vO;
        void main(){
          vec3 N = normalize(vN), L = normalize(uL - vW), V = normalize(cameraPosition - vW);
          float c = cos(uRot), s = sin(uRot);
          vec3 o = normalize(vec3(c * vO.x + s * vO.z, vO.y, -s * vO.x + c * vO.z));
          vec3 alb;
          if (uType < 0.5) {            // 地球
            float land = smoothstep(0.02, 0.08, fbm(o * 2.2 + uSeed));
            float ice = smoothstep(0.82, 0.9, abs(o.y));
            alb = mix(vec3(0.03, 0.09, 0.22), mix(vec3(0.16, 0.24, 0.10), vec3(0.42, 0.34, 0.22), smoothstep(0.1, 0.4, fbm(o * 6.0))), land);
            alb = mix(alb, vec3(0.9), ice);
            float cl = smoothstep(0.1, 0.5, fbm(o * 4.0 + vec3(0.0, 0.0, uSeed * 2.0)));
            alb = mix(alb, vec3(0.95), cl * 0.75);
          } else if (uType < 1.5) {     // 木星
            float lat = o.y + 0.04 * fbm(o * 6.0 + uSeed);
            float b = sin(lat * 26.0) * 0.5 + 0.5;
            alb = mix(vec3(0.62, 0.48, 0.34), vec3(0.88, 0.80, 0.68), b);
            alb = mix(alb, vec3(0.55, 0.30, 0.18), smoothstep(0.6, 0.9, sin(lat * 9.0 + 1.0)) * 0.5);
          } else if (uType < 2.5) {     // 月球
            float g = fbm(o * 4.0 + uSeed);
            alb = vec3(0.42) * (0.75 + 0.35 * g) - smoothstep(0.25, 0.5, fbm(o * 1.5 + 7.0)) * 0.15;
          } else {                      // 岩质行星
            float g = fbm(o * 3.0 + uSeed);
            alb = mix(vec3(0.28, 0.12, 0.08), vec3(0.55, 0.38, 0.30), g * 0.5 + 0.5);
          }
          alb *= uTint;
          float d = max(dot(N, L), 0.0);
          vec3 col = alb * uLC * pow(d, 0.9) * 1.6 + alb * 0.012;
          float rim = pow(1.0 - max(dot(N, V), 0.0), 3.0);
          vec3 atm = uType < 0.5 ? vec3(0.35, 0.6, 1.0) : uType < 1.5 ? vec3(0.8, 0.65, 0.5) : vec3(0.0);
          col += atm * rim * smoothstep(-0.2, 0.4, dot(N, L)) * 0.9;
          gl_FragColor = vec4(col, uA);
        }`,
    });
    const m = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), mat);
    scene.add(m);
    planets.push({ m, mat });
  }

  // 粗线：Line2，按段写入，每帧原地更新
  const mkLine2 = (cap) => {
    const geo = new LineGeometry();
    geo.setPositions(new Float32Array((cap + 1) * 3));
    geo.setColors(new Float32Array((cap + 1) * 3));
    const lm = new LineMaterial({ linewidth: 1.6, vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, worldUnits: false });
    lm.resolution.set(W, H);
    const l = new Line2(geo, lm);
    l.frustumCulled = false;
    scene.add(l);
    return { l, geo, lm, cap };
  };
  const trails = Array.from({ length: N_TRAIL }, () => mkLine2(TRAIL_CAP));
  // 细线：1 像素，大量轨迹用
  const thins = Array.from({ length: N_THIN }, () => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(THIN_CAP * 3), 3));
    g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(THIN_CAP * 3), 3));
    const l = new THREE.Line(g, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    l.frustumCulled = false;
    scene.add(l);
    return { l, g };
  });

  // 点云（特洛伊小行星等）
  const CLOUD_CAP = 12000;
  const cloud = (() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(CLOUD_CAP * 3), 3));
    g.setAttribute('seed', new THREE.BufferAttribute(Float32Array.from({ length: CLOUD_CAP }, (_, i) => (Math.sin(i * 12.9898) * 43758.5453) % 1), 1));
    const mat = new THREE.ShaderMaterial({
      uniforms: { uCol: { value: new THREE.Color() }, uA: { value: 1 }, uSize: { value: 2 } }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      vertexShader: `attribute float seed; uniform float uSize; varying float vB;
        void main(){ vB = 0.5 + 0.5 * abs(seed); vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_PointSize = uSize * (0.6 + abs(seed)); gl_Position = projectionMatrix * mv; }`,
      fragmentShader: `uniform vec3 uCol; uniform float uA; varying float vB;
        void main(){ float d = length(gl_PointCoord - 0.5); gl_FragColor = vec4(uCol * vB * uA * smoothstep(0.5, 0.1, d), 1.0); }`,
    });
    const p = new THREE.Points(g, mat);
    p.frustumCulled = false;
    scene.add(p);
    return { p, g, mat };
  })();

  // 三体星球地表（地平线镜头）
  const horizon = (() => {
    const geo = new THREE.SphereGeometry(1, 1400, 300, Math.PI * 7 / 6, Math.PI * 2 / 3, 0, 0.3);
    const mat = new THREE.ShaderMaterial({
      uniforms: U,
      vertexShader: NOISE + `varying vec3 vW; varying vec3 vO; varying float vH;
        float ridge(vec3 p){ float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * (1.0 - abs(snoise(p))); p *= 2.1; a *= 0.5; } return s; }
        void main(){
          vec3 p = normalize(position);
          float h = pow(ridge(p * 22.0), 1.7) * 0.008 + fbm(p * 9.0) * 0.003;
          vH = h; vO = p;
          vec4 w = modelMatrix * vec4(p * (1.0 + h), 1.0);
          vW = w.xyz;
          gl_Position = projectionMatrix * viewMatrix * w;
        }`,
      fragmentShader: NOISE + `
        uniform vec3 uS[4]; uniform vec3 uC[4];
        varying vec3 vW; varying vec3 vO; varying float vH;
        void main(){
          vec3 N = normalize(cross(dFdx(vW), dFdy(vW)));
          vec3 V = normalize(cameraPosition - vW);
          if (dot(N, V) < 0.0) N = -N;
          float g = fbm(vO * 120.0);
          vec3 alb = mix(vec3(0.10, 0.085, 0.075), vec3(0.30, 0.25, 0.20), smoothstep(0.0, 0.012, vH)) * (0.8 + 0.4 * g);
          vec3 col = vec3(0.0), fogc = vec3(0.006, 0.006, 0.01);
          float rimv = pow(1.0 - max(dot(N, V), 0.0), 3.0);
          for (int i = 0; i < 4; i++) {
            vec3 L = normalize(uS[i] - vW);
            col += alb * uC[i] * pow(max(dot(N, L), 0.0), 1.3) * 1.5;
            float back = pow(max(dot(-V, -L), 0.0), 6.0);
            col += uC[i] * rimv * back * 0.35;
            fogc += uC[i] * pow(max(dot(-V, -L), 0.0), 10.0) * 0.08;
          }
          float dist = length(cameraPosition - vW);
          col = mix(col, fogc, 1.0 - exp(-dist * 0.9));
          gl_FragColor = vec4(col, 1.0);
        }`,
    });
    mat.extensions = { derivatives: true };
    const m = new THREE.Mesh(geo, mat);
    scene.add(m);
    return m;
  })();

  // 铅笔 + 桌面（第二章“立着的铅笔”）
  const desk = (() => {
    const g = new THREE.Group();
    const table = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({ color: 0x3a2c20, roughness: 0.45, metalness: 0.05 }));
    table.rotation.x = -Math.PI / 2;
    g.add(table);
    const pencil = new THREE.Group();
    const L = 1.0, r = 0.035;
    const wood = new THREE.Mesh(new THREE.CylinderGeometry(r, r, L * 0.86, 6), new THREE.MeshStandardMaterial({ color: 0xc8962e, roughness: 0.35, metalness: 0.1 }));
    wood.position.y = L * 0.07 + L * 0.43;
    const band = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.02, r * 1.02, 0.05, 24), new THREE.MeshStandardMaterial({ color: 0xc9a25a, roughness: 0.25, metalness: 0.9 }));
    band.position.y = L * 0.93;
    const tip = new THREE.Mesh(new THREE.ConeGeometry(r, L * 0.07 * 1.0, 6), new THREE.MeshStandardMaterial({ color: 0xd8c3a0, roughness: 0.7 }));
    tip.rotation.x = Math.PI; tip.position.y = L * 0.035;
    pencil.add(wood, band, tip);
    g.add(pencil);
    const key = new THREE.SpotLight(0xffd7a0, 30, 20, 0.6, 0.5, 1.2); key.position.set(2.5, 4, 2); key.target = pencil;
    const rim = new THREE.PointLight(0x6fa8ff, 4, 10, 1.2); rim.position.set(-2, 1.5, -2);
    g.add(key, rim, new THREE.AmbientLight(0x404858, 0.5));
    scene.add(g);
    return { g, pencil };
  })();

  // 后期
  const Anamorphic = {
    uniforms: { tDiffuse: { value: null }, uAmt: { value: 0.55 } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
    fragmentShader: `uniform sampler2D tDiffuse; uniform float uAmt; varying vec2 vUv;
      void main(){
        vec4 base = texture2D(tDiffuse, vUv);
        vec3 s = vec3(0.0);
        for (int i = -24; i <= 24; i++) {
          float o = float(i) / 24.0;
          vec3 c = texture2D(tDiffuse, vUv + vec2(o * 0.35, 0.0)).rgb;
          s += max(c - 1.4, 0.0) * exp(-abs(o) * 4.0);
        }
        gl_FragColor = vec4(base.rgb + s / 24.0 * vec3(0.45, 0.65, 1.25) * uAmt, base.a);
      }`,
  };
  const Grade = {
    uniforms: { tDiffuse: { value: null }, uT: { value: 0 }, uVig: { value: 1 } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
    fragmentShader: `uniform sampler2D tDiffuse; uniform float uT; uniform float uVig; varying vec2 vUv;
      float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
      void main(){
        vec2 d = vUv - 0.5;
        float ca = 0.0018 * length(d) * 2.0;
        vec3 c = vec3(texture2D(tDiffuse, vUv + d * ca).r, texture2D(tDiffuse, vUv).g, texture2D(tDiffuse, vUv - d * ca).b);
        float l = dot(c, vec3(0.299, 0.587, 0.114));
        c = mix(c, c * vec3(0.92, 1.0, 1.1), smoothstep(0.5, 0.0, l));
        c = mix(c, c * vec3(1.06, 1.0, 0.92), smoothstep(0.4, 1.0, l));
        c *= 1.0 - 0.55 * uVig * pow(length(d * vec2(1.0, 0.8)) * 1.35, 2.2);
        c += (h(vUv * 1000.0 + uT) - 0.5) * 0.03;
        gl_FragColor = vec4(c, 1.0);
      }`,
  };
  const composer = new EffectComposer(renderer);
  composer.setPixelRatio(1);
  composer.setSize(W, H);
  composer.addPass(new RenderPass(scene, camera));
  const ana = new ShaderPass(Anamorphic);
  composer.addPass(ana);
  const bloom = new UnrealBloomPass(new THREE.Vector2(W, H), 0.9, 0.75, 0.75);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());
  const grade = new ShaderPass(Grade);
  composer.addPass(grade);

  let size = [W, H];
  const setSize = (w, h) => {
    if (size[0] === w && size[1] === h) return;
    size = [w, h];
    renderer.setSize(w, h, false);
    composer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    trails.forEach((T) => T.lm.resolution.set(w, h));
  };

  const col = new THREE.Color();
  const tmp = new THREE.Vector3();
  function writeLine2(T, pts, n, c, a, w, fadePow) {
    const ps = T.geo.attributes.instanceStart.data.array, cs = T.geo.attributes.instanceColorStart.data.array;
    n = Math.min(n, T.cap + 1);
    col.set(c);
    for (let i = 0; i < n - 1; i++) {
      const u0 = n > 1 ? i / (n - 1) : 1, u1 = (i + 1) / (n - 1);
      const a0 = a * (fadePow ? Math.pow(u0, fadePow) : 1), a1 = a * (fadePow ? Math.pow(u1, fadePow) : 1);
      ps[6 * i] = pts[3 * i]; ps[6 * i + 1] = pts[3 * i + 1]; ps[6 * i + 2] = pts[3 * i + 2];
      ps[6 * i + 3] = pts[3 * i + 3]; ps[6 * i + 4] = pts[3 * i + 4]; ps[6 * i + 5] = pts[3 * i + 5];
      cs[6 * i] = col.r * a0; cs[6 * i + 1] = col.g * a0; cs[6 * i + 2] = col.b * a0;
      cs[6 * i + 3] = col.r * a1; cs[6 * i + 4] = col.g * a1; cs[6 * i + 5] = col.b * a1;
    }
    T.geo.attributes.instanceStart.data.needsUpdate = true;
    T.geo.attributes.instanceColorStart.data.needsUpdate = true;
    T.geo.instanceCount = Math.max(0, n - 1);
    T.lm.linewidth = w;
    T.l.visible = n > 1;
  }

  // cfg 见 shots.js：cam / stars / planets / trails / thins / cloud / dust / horizon / desk / exposure / bloom / size
  function draw(cfg) {
    const [w, h] = cfg.size || [W, H];
    setSize(w, h);
    const t = cfg.t || 0;
    U.uT.value = t;
    grade.uniforms.uT.value = t;
    grade.uniforms.uVig.value = cfg.vig ?? 1;
    renderer.toneMappingExposure = cfg.exposure ?? 1;
    bloom.strength = cfg.bloom ?? 0.9;
    ana.uniforms.uAmt.value = cfg.ana ?? 0.55;

    const c = cfg.cam;
    camera.fov = c.fov ?? 32;
    camera.near = c.near ?? 0.002;
    camera.far = c.far ?? 9000;
    camera.updateProjectionMatrix();
    camera.position.set(...c.pos);
    camera.up.set(...(c.up || [0, 1, 0]));
    camera.lookAt(...c.look);
    if (c.roll) camera.rotateZ(c.roll);
    camera.updateMatrixWorld();
    sky.position.copy(camera.position);
    sky.userData.mat.uniforms.uA.value = cfg.sky ?? 1;
    sky.userData.pm.opacity = cfg.sky ?? 1;

    const S = cfg.stars || [];
    for (let j = 0; j < N_STAR; j++) {
      const st = stars[j], s = S[j];
      const on = !!s && (s.a ?? 1) > 0;
      st.body.visible = st.glow.visible = on;
      if (!on) { U.uS.value[j].set(1e6, 1e6, 1e6); U.uC.value[j].setRGB(0, 0, 0); continue; }
      const p = tmp.set(...s.p);
      const R = s.r ?? 0.04;
      let dmin = Infinity;
      for (let i = 0; i < S.length; i++) if (i !== j && S[i]) dmin = Math.min(dmin, p.distanceTo(new THREE.Vector3(...S[i].p)));
      const sc = s.noShrink ? 1 : Math.min(1, (0.46 * dmin) / R);
      st.body.position.copy(p);
      st.body.scale.setScalar(R * sc);
      st.glow.position.copy(p);
      const dcam = camera.position.distanceTo(p);
      st.glow.scale.setScalar((Math.min(R, 0.05) * 12 + R * 2) * Math.max(1, dcam / (s.glowRef ?? 2.6)) * (s.glow ?? 1));
      st.mat.uniforms.uCol.value.set(s.col);
      st.mat.uniforms.uA.value = s.a ?? 1;
      st.glow.material.color.set(s.col).multiplyScalar(1.6 * (s.a ?? 1) * (s.glowA ?? 1));
      U.uS.value[j].copy(p);
      U.uC.value[j].set(s.col).multiplyScalar((s.a ?? 1) * (s.light ?? 1));
    }

    const P = cfg.planets || [];
    for (let j = 0; j < N_PLANET; j++) {
      const pl = planets[j], q = P[j];
      pl.m.visible = !!q && (q.a ?? 1) > 0;
      if (!pl.m.visible) continue;
      pl.m.position.set(...q.p);
      pl.m.scale.setScalar(q.r);
      const u = pl.mat.uniforms;
      u.uType.value = { earth: 0, jupiter: 1, moon: 2, rock: 3 }[q.type || 'earth'];
      u.uL.value.set(...(q.light || [0, 0, 0]));
      u.uLC.value.set(q.lightCol || '#fff4e0');
      u.uA.value = q.a ?? 1;
      u.uRot.value = q.rot ?? t * 0.3;
      u.uTint.value.set(q.tint || '#ffffff');
      pl.mat.depthWrite = (q.a ?? 1) >= 1;
    }

    const TR = cfg.trails || [];
    for (let j = 0; j < N_TRAIL; j++) {
      const q = TR[j];
      if (!q) { trails[j].l.visible = false; continue; }
      writeLine2(trails[j], q.pts, q.n ?? q.pts.length / 3, q.col, q.a ?? 0.7, q.w ?? 1.6, q.fade ?? 1.6);
    }

    const TH = cfg.thins || [];
    for (let j = 0; j < N_THIN; j++) {
      const L = thins[j], q = TH[j];
      if (!q) { L.l.visible = false; continue; }
      const n = Math.min(q.n ?? q.pts.length / 3, THIN_CAP);
      const pa = L.g.attributes.position.array, ca = L.g.attributes.color.array;
      pa.set(q.pts.subarray ? q.pts.subarray(0, n * 3) : q.pts.slice(0, n * 3));
      col.set(q.col);
      for (let i = 0; i < n; i++) {
        const a = (q.a ?? 0.5) * (q.fade ? Math.pow(i / Math.max(1, n - 1), q.fade) : 1);
        ca[3 * i] = col.r * a; ca[3 * i + 1] = col.g * a; ca[3 * i + 2] = col.b * a;
      }
      L.g.attributes.position.needsUpdate = L.g.attributes.color.needsUpdate = true;
      L.g.setDrawRange(0, n);
      L.l.visible = n > 1;
    }

    const cl = cfg.cloud;
    cloud.p.visible = !!cl;
    if (cl) {
      const n = Math.min(cl.n, CLOUD_CAP);
      cloud.g.attributes.position.array.set(cl.pos.subarray(0, n * 3));
      cloud.g.attributes.position.needsUpdate = true;
      cloud.g.setDrawRange(0, n);
      cloud.mat.uniforms.uCol.value.set(cl.col || '#cfd8ff');
      cloud.mat.uniforms.uA.value = cl.a ?? 1;
      cloud.mat.uniforms.uSize.value = cl.size ?? 2;
    }

    const du = cfg.dust;
    dust.visible = !!du;
    if (du) {
      dust.position.set(...(du.center || [0, 0, 0]));
      dust.scale.setScalar(du.scale ?? 1);
      dust.material.uniforms.uA.value = du.a ?? 1;
      dust.material.uniforms.uK.value = du.scale ?? 1;
    }

    const hz = cfg.horizon;
    horizon.visible = !!hz;
    if (hz) { horizon.scale.setScalar(hz.scale ?? 3.2); horizon.position.set(...hz.p); horizon.rotation.y = hz.rotY ?? 0; }

    const dk = cfg.desk;
    desk.g.visible = !!dk;
    if (dk) {
      desk.g.position.set(...(dk.p || [0, 0, 0]));
      desk.pencil.rotation.set(0, 0, 0);
      desk.pencil.rotation.z = -dk.theta;
    }

    composer.render();
    return canvas;
  }

  // 世界坐标 → 当前画布像素（含视口偏移由调用方处理）
  function project(p) {
    const v = tmp.set(...p).project(camera);
    return [(v.x * 0.5 + 0.5) * size[0], (-v.y * 0.5 + 0.5) * size[1], v.z];
  }
  function camDist(p) { return camera.position.distanceTo(tmp.set(...p)); }

  return { draw, project, camDist, canvas, THREE };
}
