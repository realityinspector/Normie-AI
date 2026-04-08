/**
 * Lightweight analytics — fire-and-forget event tracking via sendBeacon.
 */
(function() {
  function send(event, page, metadata) {
    try {
      var data = JSON.stringify({ event: event, page: page || null, metadata: metadata || null });
      if (navigator.sendBeacon) {
        navigator.sendBeacon('/analytics/event', new Blob([data], { type: 'application/json' }));
      } else {
        fetch('/analytics/event', { method: 'POST', credentials: 'include',
          headers: { 'Content-Type': 'application/json' }, body: data, keepalive: true }).catch(function() {});
      }
    } catch (e) { /* silent */ }
  }

  window.trackEvent = function(name, metadata) { send(name, location.pathname, metadata); };

  document.addEventListener('DOMContentLoaded', function() {
    send('page_view', location.pathname, { referrer: document.referrer || null });
  });
})();
