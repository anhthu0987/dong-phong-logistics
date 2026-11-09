// End-to-end Socket.IO test through Nginx, using private temporary credentials.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { io } = require(require.resolve('socket.io-client', { paths: ['/home/frappe/frappe-bench/apps/frappe'] }));
const config = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const base = 'http://frontend:8080';
const namespace = '/' + config.site;
const token = user => `token ${user.api_key}:${user.api_secret}`;
const sockets = [];
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function api(method, data, user) {
  const response = await fetch(base + '/api/method/' + method, {
    method: 'POST', headers: { Authorization: token(user), 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  const body = await response.json();
  if (response.status !== 200 && user === config.reader) console.error(method + ': ' + (body.exc || body.exception || 'HTTP ' + response.status));
  return { status: response.status, message: body.message };
}
function socket(user, origin = 'http://localhost:8086') {
  const client = io(base + namespace, { transports: ['websocket'], autoConnect: false,
    reconnection: false, extraHeaders: { Authorization: token(user), Origin: origin, Host: "localhost:8086" } });
  sockets.push(client);
  return client;
}
function connect(client) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => finish(new Error('Socket connection timeout')), 10000);
    function finish(error) {
      clearTimeout(timer); client.off('connect', ready); client.off('connect_error', fail);
      error ? reject(error) : resolve();
    }
    const ready = () => finish();
    const fail = error => finish(error);
    client.once('connect', ready); client.once('connect_error', fail); client.connect();
  });
}
function simulate() {
  return new Promise((resolve, reject) => {
    const child = spawn('/home/frappe/frappe-bench/env/bin/python', [
      '/home/frappe/frappe-bench/apps/dp_dispatch/dp_dispatch/dp_dispatch/simulator.py', '--config', process.argv[2],
    ], { stdio: ['ignore', 'ignore', 'pipe'] });
    let errors = '';
    child.stderr.on('data', chunk => { errors += chunk; });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolve() : reject(new Error('Simulator failed: ' + errors)));
  });
}
async function main() {
  const reader = socket(config.reader), outsider = socket(config.outsider);
  const received = [], leaked = [];
  reader.on('dp_gps_position', point => received.push(point));
  outsider.on('dp_gps_position', point => leaked.push(point));
  await Promise.all([connect(reader), connect(outsider)]);
  assert.equal(reader.io.engine.transport.name, 'websocket');
  await assert.rejects(connect(socket(config.reader, 'http://untrusted.invalid')), /Invalid origin/);
  assert.equal((await api('dp_dispatch.dp_tracking_and_pod.realtime.watch_trip', {delivery_trip:config.delivery_trip},config.outsider)).status,403);
  assert.equal((await api('dp_dispatch.dp_tracking_and_pod.realtime.watch_trip', {delivery_trip:config.delivery_trip},config.reader)).status,200);
  await simulate();
  for(let i=0;i<30 && received.length<20;i++) await delay(100);
  assert.equal(received.length,20,'Every simulator point must arrive over WebSocket');
  assert.equal(leaked.length,0,'Unauthorized socket must receive no GPS data');
  assert.ok(received.every(p=>p.delivery_trip===config.delivery_trip && p.vehicle===config.vehicle));
  assert.equal(received.at(-1).latitude,10.9804);
  // Exercise missed messages: disconnected client uses the authorized HTTP snapshot.
  reader.disconnect();
  await simulate();
  const fallback = await api('dp_dispatch.tracking.get_trip_tracking',{delivery_trip:config.delivery_trip},config.reader);
  assert.equal(fallback.status,200);
  assert.equal(fallback.message.position.latitude,10.9804);
  assert.equal(received.length,20);
  await connect(reader);
  await api('dp_dispatch.dp_tracking_and_pod.realtime.watch_trip',{delivery_trip:config.delivery_trip},config.reader);
  await simulate();
  for(let i=0;i<30 && received.length<40;i++) await delay(100);
  assert.equal(received.length,40,'Push must resume after reconnect');
  assert.equal(leaked.length,0);
  console.log(JSON.stringify({transport:'websocket',simulator_points:60,push_received:40,
    disconnected_points_recovered_by_snapshot:20,unauthorized_events:0,invalid_origin_rejected:true,reconnect:true}));
}
main().catch(error => {console.error(error.stack); process.exitCode=1;}).finally(()=>sockets.forEach(s=>s.disconnect()));
