const CACHE_NAME = 'mycitynews-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/ad-redirect.html',
  '/articles.json',
  '/manifest.json'
];

// Install event - cache resources
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Caching files');
        return cache.addAll(urlsToCache);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log('Service Worker: Clearing old cache');
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }

        // Clone the request
        const fetchRequest = event.request.clone();

        return fetch(fetchRequest).then(response => {
          // Check if valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response
          const responseToCache = response.clone();

          // Cache the new response
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });

          return response;
        }).catch(() => {
          // Network failed, return offline page if available
          return caches.match('/index.html');
        });
      })
  );
});

// Background sync for offline functionality (optional)
self.addEventListener('sync', event => {
  if (event.tag === 'sync-articles') {
    event.waitUntil(syncArticles());
  }
});

async function syncArticles() {
  try {
    const response = await fetch('/articles.json');
    const data = await response.json();
    const cache = await caches.open(CACHE_NAME);
    await cache.put('/articles.json', new Response(JSON.stringify(data)));
    console.log('Service Worker: Articles synced');
  } catch (error) {
    console.error('Service Worker: Sync failed', error);
  }
}

// Push notifications (optional - for future use)
self.addEventListener('push', event => {
  const options = {
    body: event.data ? event.data.text() : 'New articles available!',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    vibrate: [200, 100, 200],
    tag: 'news-notification',
    actions: [
      {
        action: 'open',
        title: 'Read Now'
      },
      {
        action: 'close',
        title: 'Close'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('MyCityNews.ca', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'open') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});
