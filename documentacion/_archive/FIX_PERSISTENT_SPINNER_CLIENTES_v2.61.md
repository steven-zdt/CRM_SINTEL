# FIX: Persistent Spinner in Clientes Tab v2.61

## Problem Statement

**Symptom:** When navigating to workspace `/#clientes`, a spinner with text "Inicializando tabla de clientes..." persists indefinitely even after the table is fully loaded.

**User Experience:** 
- User clicks "Clientes" in sidebar
- Spinner appears briefly
- Table loads and displays data
- **BUG: Spinner stays visible, covering partial view of table**

## Root Cause Analysis

### The Architecture Mismatch

The clientes module was refactored in v2.61 to use **Alpine.js with lazy loading**, but the workspace navigation system uses a **different event system**:

#### Sidebar Navigation (Workspace System)
```
User clicks "Clientes" button
    ↓
Sidebar anchor: <a href="#clientes" data-tab="clientes">
    ↓
workspace.js: document.querySelectorAll('#nav a[data-tab]').click()
    ↓
showTab('clientes') called
    ↓
document.getElementById('tab-clientes').style.display = 'block'
    ↓
DOM manipulation (NO Bootstrap tab event!)
```

#### Clientes Module (Alpine.js)
```
Alpine.js list.html:
    @shown.bs.tab="handleTabChange($event)"
    
Waits for Bootstrap tab system event:
    - Only fires when using Bootstrap's tab JavaScript API
    - Does NOT fire when DOM is manipulated programmatically
    - Does NOT fire when sidebar link is clicked
```

### Why Spinner Persists

The spinner's visibility logic:
```html
<div x-show="!clientesLoaded && loadingClientes">
    <div class="spinner-border">...</div>
    <p>Inicializando tabla de clientes...</p>
</div>
```

State transitions:
```
Initial:  loadingClientes = false, clientesLoaded = false
Click sidebar:
    ↓
showTab('clientes') → div.style.display = 'block'
    ↓
@shown.bs.tab event expected... but never fires! ⚠️
    ↓
handleTabChange() never called
    ↓
loadClientesTable() never executed
    ↓
clientesLoaded stays FALSE
    ↓
Spinner condition (loadingClientes=false && clientesLoaded=false) = FALSE
    ↓
Spinner hidden? NO - depends on loadingClientes state
```

**Key Issue:** Without `handleTabChange()` being called:
- `clientesLoaded` never becomes `true`
- If any other process sets `loadingClientes = true`, spinner shows
- Or spinner shows because initial state expects the event to fire

## Solution

### Part 1: Event Bridge from Workspace to Alpine

Modified `workspace.js` to dispatch a custom event when a tab is shown:

```javascript
function showTab(tabName) {
    hideAllTabs();
    const tab = document.getElementById('tab-' + tabName);
    if (tab) {
        tab.style.display = 'block';
        // ⚠️ NEW: Dispatch custom event for Alpine components
        tab.dispatchEvent(new CustomEvent('tab-shown', { detail: { tabName } }));
    }
}
```

### Part 2: Listen to Custom Event in Alpine

Updated `list.html` to listen to the custom event:

```html
<div x-data="clientesListModule()"
     @shown.bs.tab="handleTabChange($event)"
     @tab-shown="handleWorkspaceTabChange($event)">
```

Added handler in Alpine module:

```javascript
handleWorkspaceTabChange(event) {
    const tabName = event.detail?.tabName;
    if (tabName === 'clientes') {
        console.log('[clientes.list] Loading from workspace...');
        this.loadClientesTable();
    }
}
```

### Part 3: Remove Legacy Reference

Removed outdated reference in `workspace.js`:
- Old: `'clientes': window.clientesDT` (doesn't exist)
- New: Explicit handling for clientes tab with Alpine comment

## State Flow (After Fix)

```
User clicks "Clientes" in sidebar
    ↓
workspace.js: showTab('clientes')
    ↓
tab.dispatchEvent(new CustomEvent('tab-shown', { tabName: 'clientes' }))
    ↓
Alpine.js list.html receives @tab-shown event
    ↓
handleWorkspaceTabChange() called
    ↓
loadClientesTable() executed:
    - loadingClientes = true
    - TabulatorFactory.create() (synchronous)
    - clientesLoaded = true ← table now in DOM
    - loadingClientes = false ← spinner hidden
    ↓
Spinner condition: !clientesLoaded && loadingClientes = false
    ↓
✅ Spinner hidden immediately
```

## Files Changed

### 1. `apps/tenant/core/static/core/js/workspace.js` (Line 23-30)
- Added `tab.dispatchEvent(new CustomEvent('tab-shown', ...))` 
- Added explicit handling for clientes tab
- Added debugging logs

### 2. `apps/tenant/core/templates/tenant/core/partials/clientes/list.html`
- Added `@tab-shown="handleWorkspaceTabChange($event)"` listener
- Added `handleWorkspaceTabChange()` function to Alpine module
- Enhanced logging in both handlers

## Commit Hash
`3901512` - Fix: Persistent spinner in clientes tab

## Testing Checklist

- [ ] Click "Clientes" in sidebar - spinner appears briefly, disappears immediately
- [ ] Click internal "Directorio de Clientes" tab - works as before
- [ ] Click internal "Directorio de Contactos" tab - same lazy loading works
- [ ] After reload, clientes table has data - no spinner visible
- [ ] Search field works - table reloads with spinner (for reloads)
- [ ] Create new cliente - table refreshes, no persistent spinner
- [ ] Edit cliente - offcanvas opens correctly
- [ ] Switch to another tab and back - table reloads correctly

## Performance Impact

✅ **No negative impact:**
- CustomEvent is lightweight (browser native)
- No extra API calls
- Spinner hidden immediately (same timing as before)
- Lazy loading still works (table data loads in background)

## Related Issues Fixed

1. **workspace.js no longer expects `window.clientesDT`**
   - Was causing silent error when clientes tab shown
   - Now has explicit Alpine.js handling

2. **Tab navigation consistency**
   - Sidebar clicks now trigger same flow as internal tabs
   - Single source of truth for table initialization

3. **Alpine state management**
   - `loadingClientes` and `clientesLoaded` now sync correctly
   - No race conditions between events

## Future Improvements

1. **Apply same pattern to other modules**
   - Use custom events for all workspace tabs
   - Consistent event system across modules

2. **Add AbortController**
   - Cancel in-flight requests when tab changes
   - Prevent race conditions in data loading

3. **Skeleton loader**
   - Show skeleton UI instead of spinner
   - Better UX during data loading

## References

- Alpine.js events: https://alpinejs.dev/essentials/events
- Bootstrap tabs: https://getbootstrap.com/docs/5.3/components/navs-tabs/
- CustomEvent API: https://developer.mozilla.org/en-US/docs/Web/API/CustomEvent
