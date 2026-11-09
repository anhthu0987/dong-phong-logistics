// Run with: node tests/test_frontend_regressions.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..', 'dp_dispatch');

async function main() {
  const source = fs.readFileSync(path.join(root, 'public/js/delivery_confirmation.js'), 'utf8');
  let resolveRequest, prompts = 0, handlers;
  const context = {
    frappe: {
      // jQuery Deferred is thenable, but has no Promise.finally.
      call: () => ({ then(resolve) { resolveRequest = resolve; } }),
      prompt: () => prompts++,
      ui: { form: { on: (_, callbacks) => { handlers = callbacks; } } },
      msgprint: () => {},
    },
    __: text => text,
    console,
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  const frm = {
    doc: { delivery_trip: 'TRIP' }, is_new: () => true,
    set_value: () => { throw new Error('Must not overwrite the selected stop'); },
  };
  context.dp_load_confirmation_stops(frm);
  await new Promise(setImmediate);
  frm.doc.delivery_stop = 'SELECTED-STOP';
  resolveRequest({ message: [{ value: 'A' }, { value: 'B' }] });
  await new Promise(setImmediate);
  assert.equal(prompts, 0, 'Late lookup must preserve a route-selected stop');
  assert.equal(frm.__dp_loading_stops, false, 'Thenable must settle and release loading flag');
  frm.__dp_last_trip = 'TRIP';
  handlers.delivery_trip(frm);
  assert.equal(frm.doc.delivery_stop, 'SELECTED-STOP');
  frm.fields_dict = {};
  let loadedRows = [], triggered = '';
  frm.trigger = event => { triggered = event; };
  handlers.refresh(frm);
  assert.equal(triggered, 'delivery_stop', 'Route defaults must load source items on refresh');
  context.frappe.call = () => Promise.resolve({ message: {
    delivery_order: 'ORDER', operation: 'Pickup', shipping_fee: 0,
    items: [{ allocated_qty: 40, description: 'Cartons' }],
  } });
  frm.set_value = (field, value) => { frm.doc[field] = value; };
  frm.clear_table = () => { loadedRows = []; };
  frm.add_child = (_, row) => loadedRows.push(row);
  frm.refresh_field = () => {};
  await handlers.delivery_stop(frm);
  assert.equal(frm.doc.operation, 'Pickup');
  assert.equal(frm.doc.delivery_order, 'ORDER');
  assert.equal(loadedRows[0].pending_qty, 40);
  assert.equal(frm.__dp_loaded_stop, 'SELECTED-STOP');
  assert.equal(frm.__dp_loading_details, null);

  const mapSource = fs.readFileSync(path.join(root, 'dp_dispatch/page/fleet_map/fleet_map.js'), 'utf8');
  const loader = mapSource.slice(mapSource.indexOf('  function loadJs('), mapSource.indexOf("\n  loadCss('https"));
  let appended, called = 0, failure = '';
  const mapContext = {
    window: { L: {} }, page: { main: {} },
    $: () => ({ text: value => { failure = value; } }),
    document: { createElement: () => ({}), head: { appendChild: script => { appended = script; } } },
  };
  vm.createContext(mapContext);
  vm.runInContext(loader, mapContext);
  mapContext.loadJs('test-url', () => called++);
  assert.ok(appended, 'Partial L namespace must not skip loading Leaflet');
  assert.equal(called, 0);
  mapContext.window.L.map = () => {};
  appended.onload();
  assert.equal(called, 1);
  appended = null;
  mapContext.loadJs('test-url', () => called++);
  assert.equal(appended, null);
  assert.equal(called, 2);
  delete mapContext.window.L.map;
  mapContext.loadJs('test-url', () => called++);
  appended.onerror();
  assert.ok(failure, 'Library load failure must be visible');
  console.log('Frontend regression checks passed');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
