
importScripts("https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "BLD-2ZPTshszlUU3o8LCMnFb4LucoMf5IEgCHDbClppkFzfe_2bJy-xQpObr45MPzQ-9KD6Dz3jA5wZkRxB9HP4",
  authDomain: "smart-parking-14cf6.firebaseapp.com",
  projectId: "smart-parking-14cf6",
  storageBucket: "smart-parking-14cf6.firebasestorage.app",
  messagingSenderId: "210196723755",
  appId: "1:210196723755:web:06cda784cf95eca2e9126e"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const title = payload.notification?.title || "Smart Parking";
  const options = {
    body: payload.notification?.body || "Parking status has changed.",
    icon: "/favicon.ico"
  };

  self.registration.showNotification(title, options);
});
