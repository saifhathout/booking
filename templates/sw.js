self.addEventListener('push', function(event) {
    let data = { head: 'K-HUB', body: 'New notification', url: '/' };
    if (event.data) { data = event.data.json(); }
    
    event.waitUntil(
        self.registration.showNotification(data.head, {
            body: data.body,
            icon: '/static/img/logo.png',
            badge: '/static/img/logo.png',
            vibrate: [200, 100, 200],
            data: { url: data.url || '/' },
            requireInteraction: true
        })
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(clients.openWindow(event.notification.data.url || '/'));
});

self.addEventListener('install', function(event) {
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(clients.claim());
});