const CACHE_NAME = 'gameon-v2';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

// Push notification
self.addEventListener('push', function(event) {
    let data = { title: 'GameOn', body: 'New notification', url: '/' };
    
    if (event.data) {
        data = event.data.json();
    }
    
    const options = {
        body: data.body,
        icon: data.icon || '/static/icons/icon-192x192.png',
        badge: data.badge || '/static/icons/icon-72x72.png',
        vibrate: [200, 100, 200],
        data: {
            url: data.url || '/'
        },
        requireInteraction: true
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Click notification
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url || '/')
    );
});

// Fetch
self.addEventListener('fetch', (event) => {
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});