const fs=require('fs'), vm=require('vm'), assert=require('assert/strict');
const src=fs.readFileSync('erpnext-local/dispatch-app/dp_dispatch/dp_dispatch/page/fleet_map/fleet_map.js','utf8');
const start=src.indexOf('    const onPosition =');
const stop=src.indexOf('    await refresh();',start);
let tick, callbacks={}, calls=[], rendered=[];
const c={snapshot:{trip:{name:'A',vehicle:'V',status:'In Transit'},position:{recorded_at:'2026-11-09 12:00:00'}},selected:'A',leaseUntil:Date.now()+90000,lastSync:Date.now(),polling:false,wrapper:{},document:{hidden:false,body:{contains:()=>true}},$:()=>({is:()=>true}),connected:()=>true,socket:{connected:true,active:true,connect:()=>calls.push('retry'),on:(n,f)=>callbacks[n]=f,off:()=>{}},frappe:{realtime:{on:(n,f)=>callbacks[n]=f,off:()=>{},connect:()=>calls.push('connect')}},connectionStatus:()=>{},render:d=>rendered.push(d.position),watch:async()=>calls.push('watch'),draw:async()=>calls.push('draw'),status:()=>{},routeLayer:{clearLayers(){}},positionLayer:{clearLayers(){}},historyLayer:{clearLayers(){}},setInterval:f=>(tick=f,1),clearInterval:()=>{},Date};
vm.createContext(c);vm.runInContext(src.slice(start,stop),c);
(async()=>{
 callbacks.dp_gps_position({delivery_trip:'B',vehicle:'V',recorded_at:'2026-11-09 12:00:01'});assert.equal(rendered.length,0);
 callbacks.dp_gps_position({delivery_trip:'A',vehicle:'V',recorded_at:'2026-11-09 11:00:00'});assert.equal(rendered.length,0);
 callbacks.dp_gps_position({delivery_trip:'A',vehicle:'V',recorded_at:'2026-11-09 12:00:01'});assert.equal(rendered.length,1);
 await tick();assert.deepEqual(calls,[]);
 c.socket.connected=false;c.connected=()=>false;callbacks.disconnect();await tick();assert.deepEqual(calls,['connect','watch','draw']);
 calls=[];c.socket.connected=true;c.connected=()=>true;callbacks.connect();await tick();assert.deepEqual(calls,['watch','draw']);
 console.log('Push marker, foreign/late rejection, connected no-poll, disconnect fallback and reconnect resync PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
